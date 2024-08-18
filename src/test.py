from anyio import create_task_group, TASK_STATUS_IGNORED
from anyio import run
from anyio.abc import TaskStatus
from factorio_rcon import AsyncRCONClient, RCONClient

from client.factorio_instance import FactorioInstance
from client.factorio_pool import FactorioPool


async def connect(rcon, *, task_status: TaskStatus = TASK_STATUS_IGNORED):
    async with rcon as listener:
        task_status.started()
        await rcon.connect()

commands = {
    "times": "/c rcon.print(1234*5678)",
    "add": "/c rcon.print(1+2)"
}



async def send(instance: AsyncRCONClient):
    #async with await instance.connect():
    positions = await instance.send_command('/c rcon.print(1*2)')
    print(positions)

async def create_clients_async(num: int, starting_ip: int = 27016):
    clients = []
    factorio_pool = FactorioPool(num, 64, starting_ip)
    for i, instance in enumerate(factorio_pool.instances):
        instance = AsyncRCONClient('localhost', starting_ip+i, "factorio")
        #await client.connect()
        await instance.connect()
        #await client.connect()
        clients.append(instance)
    return clients

def create_clients_sync(num: int, starting_ip: int = 27016):
    clients = []
    for i in range(num):
        client = RCONClient('localhost', starting_ip+i, "factorio")
        client.connect()
        clients.append(client)
    return clients


from timeit import default_timer as timer


async def connection_async(clients_num: int, num: int):
    clients = await create_clients_async(clients_num, 27016)
    time = timer()
    for i in range(num):
        async with create_task_group() as tg:
            #await tg.start(connect, rcon_client_1)
            #await tg.start(connect, rcon_client_1)
            for client in clients:
                tg.start_soon(send, client)

    end = (timer() - time)

    print("Async", clients_num, end, (timer()-time)/num, ((timer()-time)/num)/clients_num)

def connection_sync(clients_num: int, num: int):

    clients = create_clients_sync(clients_num, 27016)
    time = timer()
    for i in range(num):
        for client in clients:
            client.send_commands(commands)
    end = (timer()-time)
    print("Sync", clients_num, end, end/num, ((timer()-time)/num)/clients_num)


for i in range(1, 4):
    #connection_sync(i, 1000)
    run(connection_async, i, 10)