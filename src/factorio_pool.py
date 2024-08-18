from threading import Lock, Event
from anyio import Event
from anyio import create_task_group

from src.factorio_instance import FactorioInstance
from src.utils import print_timing


class FactorioPool:

    def __init__(self, instance_num=2, bounding_box=64, tcp_port=27015):
        self.mutex = Lock()
        self.instances = self._create(instance_num, bounding_box, tcp_port)
        self.vocabulary = {}
        self.i_vocabulary = {}

    def _create(self, instance_num, bounding_box=64, tcp_port=27015):
        instances = []
        for i in range(instance_num):
            port = tcp_port+i
            instance = FactorioInstance('localhost', self._update_vocabulary, self._get_vocabulary, bounding_box, port)
            instances.append(instance)
        return instances

    async def connect(self):
        for instance in self.instances:
            await instance.connect()

    async def initialise(self, **kwargs):
        for instance in self.instances:
            await instance.initialise(**kwargs)


    @print_timing
    async def act(self, action, *args):
        results = {}
        async with create_task_group() as tg:
            for i, instance in enumerate(self.instances):
                results[i] = {}
                tg.start_soon(instance.move, results[i], *args)
        print(action, args, results)
        return results

    @print_timing
    async def observe(self, *args):
        results = {}

        async with create_task_group() as tg:
            events = []
            for i, instance in enumerate(self.instances):
                results[i] = {}
                event = Event()
                tg.start_soon(instance.observe, results[i], event, *args)
                events.append(event)

            for event in events:
                await event.wait()
        return results


