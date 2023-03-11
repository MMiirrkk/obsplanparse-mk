from pyaraucaria.obs_plan.obs_plan_parser import ObsPlanParser
import logging
from typing import List, Any, Dict

logger = logging.getLogger("planrunner")
logger.setLevel(logging.INFO)

class CantOverideNightPlanError(Exception):
    pass

class SequenceTreeError(Exception):
    pass

class ObservationPlan:

    def __init__(self, client_name: str, observ_plan_id: str) -> None:
        self.observ_plan_id = observ_plan_id
        self.client_name = client_name
        self.subcomponents = {}
        super().__init__()

    def get_nightplan(self, nightplan_id: str):
        try:
            return self.subcomponents[nightplan_id]
        except LookupError:
            logger.error(f'There is no nightplan {nightplan_id}')

    def write_nightplan(self, nightplan_id: str, nightplan_dict: List[Any], overwrite: bool = False):

        if (nightplan_id in self.subcomponents.keys()) and overwrite:
            np = NightPlan(nightplan_id, nightplan_dict, self)
            self.subcomponents[nightplan_id] = np
            logger.info(f'Plan {nightplan_id} is overwritten')
        elif (nightplan_id in self.subcomponents.keys()) and (overwrite is False):
            raise CantOverideNightPlanError
        else:
            np = NightPlan(nightplan_id, nightplan_dict, self)
            self.subcomponents[nightplan_id] = np
            logger.info(f'Plan {nightplan_id} is written')

    def run_night(self, nightplan_id: str):
        self.subcomponents[nightplan_id].run()


class NightPlan:

    def __init__(self, nightplan_id: str, nightplan_dict: List[Any], observation_plan: 'ObservationPlan') -> None:
        self.nightplan_id = nightplan_id
        self.observation_plan = observation_plan
        self.nightplan_dict = nightplan_dict
        self.subcomponents = {}
        super().__init__()
        self.write_subcomponents()

    def write_subcomponent(self, sequence_id, sequence_dict, par_kw: Dict or None = None):
        seq = Sequence(sequence_id, sequence_dict, self, par_kw=par_kw)
        self.subcomponents[sequence_id] = seq
        logger.debug(f'Sequence {sequence_id} dict {sequence_dict} is written')

    def write_subcomponents(self):
        seq_id = 0
        for sequence_dict in self.nightplan_dict:
            self.write_subcomponent(f'{seq_id}', sequence_dict)
            seq_id += 1

    def run(self):
        logger.info(f"Running night {self.nightplan_id}")


class Sequence:

    def __init__(self, sequence_id: str, sequence_dict: Dict[Any, Any], night_plan: 'NightPlan', par_kw: Dict or None = None) -> None:
        self.sequence_id = sequence_id
        self.sequence_dict = sequence_dict
        self.args = []
        self.kwargs = {}
        self.parent_kwargs = par_kw
        self.nightplan = night_plan
        self.subcomponents = {}
        super().__init__()
        self.build_sequence_struct(par_kw)

    def build_sequence_struct(self, par_kw):

        seq_id = 0
        if par_kw:
            for n in par_kw.keys():
                self.parent_kwargs[n] = par_kw[n]
        if 'kwargs' in self.sequence_dict.keys():
            for k in self.sequence_dict['kwargs'].keys():
                self.kwargs[k] = self.sequence_dict['kwargs'][k]
        if 'all_commands' in self.sequence_dict.keys():
            for case in self.sequence_dict['all_commands']:
                if 'begin_sequence' in case.keys():
                    kw = None
                    if 'kwargs' in case.keys():
                        for k in case['kwargs'].keys():
                            self.kwargs[k] = case['kwargs'][k]
                            kw = self.kwargs
                    if self.parent_kwargs:
                        for p in self.parent_kwargs.keys():
                            kw[p] = self.parent_kwargs[p]
                    self.nightplan.write_subcomponent(f'{self.sequence_id}{seq_id}',
                                                  case, par_kw=kw)
                    seq_id += 1
                elif 'command_name' in case.keys():
                    self.write_command(f'{self.sequence_id}{seq_id}',
                                       case, par_kw=self.parent_kwargs)
                    seq_id += 1
                else:
                    raise SequenceTreeError(Exception)

    def write_command(self, command_id, command_dict, par_kw: dict = None):
        com = Command(command_id, command_dict, self, par_kw)
        self.subcomponents[command_id] = com


class Command:

    def __init__(self, command_id: str, command_dict: Dict[Any, Any], sequence: 'Sequence', par_kw: Dict or None = None) -> None:
        self.command_id = command_id
        self.command_dict = command_dict
        self.sequence = sequence
        self.args = []
        self.kwargs = {}
        self.parent_kwargs = par_kw
        self.command_name: str or None = None
        # self.executors = {}
        super().__init__()
        self.build_command_struct()


    def build_command_struct(self):
        self.command_name = self.command_dict['command_name']
        if 'args' in self.command_dict.keys():
            for m in self.command_dict['args']:
                self.args.append(m)
        if 'kwargs' in self.command_dict.keys():
            for k in self.command_dict['kwargs'].keys():
                self.kwargs[k] = self.command_dict['kwargs'][k]
        logger.debug(
            f'Command id {self.command_id} name {self.command_name} args {self.args} kwargs {self.kwargs} is written')


    

class Executor:

    def __init__(self, id: str, command: 'Command') -> None:
        self.id = id
        super().__init__()



class ChangeFilter(Executor):
    pass

class MountSlewCooSync(Executor):
    pass

class DomeSlewAz(Executor):
    pass

class CameraExposure(Executor):
    pass


class PlanRunner:

    def __init__(self, client_name: str, observ_plan_id: str):
        self.client_name = client_name
        self.observ_plan_id = observ_plan_id
        self.parsed_plan: List[Any] or None = None
        self.plan_string: str or None = None
        self.observation_plan: ObservationPlan = ObservationPlan(client_name=client_name, observ_plan_id=observ_plan_id)

    def load_night_plan_string(self, night_id: str, string: str, overwrite: bool = False) -> None:
        # TODO check if nightplan is there and ask for overrive and delete previous night plan from this day

        self.load_string(string)
        self.parse_plan()
        try:
            self.observation_plan.write_nightplan(night_id, self.parsed_plan, overwrite=overwrite)
        except CantOverideNightPlanError:
            logger.error(f'Cannot overwrite nightplan {night_id}, please select overwrite=True')

    def load_string(self, string: str) -> None:
        if self.plan_string:
            self.plan_string = string
            logger.info(f'Plan string is overwrite')
        else:
            self.plan_string = string
            logger.info(f'Plan string is loaded')
        logger.debug(f'Loaded string: {self.plan_string}')


    def parse_plan(self) -> None:
        if self.plan_string:
            parser = ObsPlanParser()
            self.parsed_plan = parser.convert_from_string(self.plan_string)
            logger.debug(f'Parsed: {self.parsed_plan}')
        else:
            logger.error(f'No plan to parse.')

    def run_night(self, night_id: str):
        self.observation_plan.run_night(night_id)




input = """BEGINSEQUENCE
               OBJECT FF_Aql 18:58:14.75 17:21:39.29 seq=5/I/60,5/V/70
               BEGINSEQUENCE focus=+30
                   OBJECT V496_Aql 19:08:20.77 -07:26:15.89 seq=1/V/20
                   OBJECT V496_Aql 19:08:20.77 -07:26:15.89 seq=1/V/20
               ENDSEQUENCE
           ENDSEQUENCE
           
           """

pr = PlanRunner('DefaultClient', 'ObervPlan11')
pr.load_night_plan_string('112232322', input)
pr.load_night_plan_string('112232333', input)
#pr.load_night_plan_string('112232322', input, overwrite=True)
#pr.run_night('112232322')
x = pr.observation_plan
x = x.subcomponents
x = x
lis = []
for n in x:
    #print(n, x[n])
    w = x[n].subcomponents
    for m in w:
        #print(m, w[m], w[m].args, w[m].kwargs)
        if isinstance(w[m], Command):
            lis.append(f'{n} {m} {w[m].command_name} {w[m].args} {w[m].kwargs} {w[m].parent_kwargs}')# {w[m].args} {w[m].kwargs}')
        try:
            z = w[m].subcomponents
            for u in z:
                #print(u, z[u], z[u].args, z[u].kwargs)
                if isinstance(z[u], Command):
                    lis.append(f'{n} {u} {z[u].command_name} {z[u].args} {z[u].kwargs} {z[u].parent_kwargs}')
        except Exception as e:
            print()

print(sorted(lis))









"""
[{'begin_sequence': 'begin', 'all_commands': [
{'command_name': 'OBJECT', 'args': ['FF_Aql', '18:58:14.75', '17:21:39.29'], 'kwargs': {'seq': '5/I/60,5/V/70'}}, 
{'begin_sequence': 'begin', 'kwargs': {'focus': '+30'}, 'all_commands': [
    {'command_name': 'OBJECT', 'args': ['V496_Aql', '19:08:20.77', '-07:26:15.89'], 'kwargs': {'seq': '1/V/20'}}, 
    {'command_name': 'OBJECT', 'args': ['V496_Aql', '19:08:20.77', '-07:26:15.89'], 'kwargs': {'seq': '1/V/20'}}
]}]}]

"""

