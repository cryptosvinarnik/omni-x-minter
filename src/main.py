import asyncio
import random

from loguru import logger

from config import DELAY_RANGE, MAX_FEE_PER_GAS, MAX_PRIORITY_FEE_PER_GAS
from omnix.const import RPC
from omnix.mint import OmniX, get_web3
from omnix.utils import init_logger


async def worker(q: asyncio.Queue,) -> None:
    while not q.empty():
        private_key = await q.get()

        try:
            omni = OmniX(get_web3(RPC), private_key)

            eip_1559_gas = await omni.eip_1559_gas

            if (
                (eip_1559_gas["maxFeePerGas"] > MAX_FEE_PER_GAS)
                and
                (eip_1559_gas["maxPriorityFeePerGas"] > MAX_PRIORITY_FEE_PER_GAS)
            ):
                logger.error(
                    f"[{omni.account.address}] Gas price is too high: {eip_1559_gas}."
                )
                q.put_nowait(private_key)
                continue

            logger.info(f"[{omni.account.address}] Trying to mint NFT.")

            tx_hash = await omni.mint()

            sleep_time = random.randint(*DELAY_RANGE)

            logger.success(
                f"[{omni.account.address}] Sent mint TX with "
                f"hash {tx_hash.hex()} and sleep for {sleep_time} seconds."
            )

            await asyncio.sleep(sleep_time)

        except Exception as e:
            logger.error(f"[{omni.account.address}] Failed with error: {e}")


async def main():
    init_logger()

    with open("accounts.txt", "r") as f:
        accounts = f.read().splitlines()

    logger.info(
        f"Loaded {len(accounts)=}. "
        f"Delay range: from {DELAY_RANGE[0]} to {DELAY_RANGE[1]} seconds. "
    )

    q = asyncio.Queue()
    for account in accounts:
        q.put_nowait(account)

    workers = [
        asyncio.create_task(worker(q))
        for _ in range(1)
    ]

    await asyncio.gather(*workers)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Exiting...")
