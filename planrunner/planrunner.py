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
            logger.info(f'NightPlan {nightplan_id} to {self.observ_plan_id} is overwritten')
        elif (nightplan_id in self.subcomponents.keys()) and (overwrite is False):
            raise CantOverideNightPlanError
        else:
            np = NightPlan(nightplan_id, nightplan_dict, self)
            self.subcomponents[nightplan_id] = np
            logger.info(f'NightPlan {nightplan_id} to {self.observ_plan_id} is written')

    def run_night(self, nightplan_id: str):
        self.subcomponents[nightplan_id].run()

class AbstractSequence:
    def __init__(self, parent: 'NightPlan' or 'Sequence'):
        super().__init__()
        self.parent = parent

    def write_subcomponent(self, sequence_id, sequence_dict):
        sub = Sequence(sequence_id, sequence_dict, self.parent)
        logger.info(f'Sequence {sequence_id} to {self.parent.sequence_id} is written')
        return sub

    def write_command(self, command_id, command_dict):
        com = Command(command_id, command_dict, self.parent)
        logger.info(f'Command {command_id} to {self.parent.sequence_id} is written')
        return com

    def build_args(self, sequence_dict: Dict[Any, Any]):
        if 'args' in sequence_dict.keys():
            return sequence_dict['args']
        else:
            return []

    def build_kwargs(self, sequence_dict: Dict[Any, Any]):
        if 'kwargs' in sequence_dict.keys():
            return sequence_dict['kwargs']
        else:
            return {}


class NightPlan(AbstractSequence):

    def __init__(self, sequence_id: str, sequence_dict: List[Any], parent: 'ObservationPlan') -> None:
        self.sequence_id = sequence_id
        self.parent = parent
        self.sequence_dict = sequence_dict
        self.subcomponents = {}
        self.args = []
        self.kwargs = {}
        self.parent_args = []
        self.parent_kwargs = {}
        super().__init__(self)
        self.write_subcomponents()

    def write_subcomponents(self):
        seq_id = 0
        for se in self.sequence_dict:
            sub = self.write_subcomponent(f'{seq_id}', se)
            self.subcomponents[f'{seq_id}'] = sub
            seq_id += 1

    def run(self):
        logger.info(f"Running night {self.sequence_id}")


class Sequence(AbstractSequence):

    def __init__(self, sequence_id: str, sequence_dict: Dict[Any, Any],
                 parent: 'NightPlan' or 'Sequence') -> None:
        self.sequence_id = sequence_id
        self.sequence_dict = sequence_dict
        self.parent = parent
        self.args = self.build_args(self.sequence_dict)
        self.kwargs = self.build_kwargs(self.sequence_dict)
        self.parent_args = self.parent.args + self.parent.parent_args
        self.parent_kwargs = self.parent.kwargs | self.parent.parent_kwargs
        self.subcomponents = {}
        self.priority: int = 0
        super().__init__(self)
        self.build_sequence()


    def build_sequence(self):

        seq_id = 0
        if 'all_commands' in self.sequence_dict.keys():
            for case in self.sequence_dict['all_commands']:
                if 'begin_sequence' in case.keys():
                    sub = self.write_subcomponent(f'{self.sequence_id}{seq_id}',case)
                    self.subcomponents[f'{self.sequence_id}{seq_id}'] = sub
                    seq_id += 1
                elif 'command_name' in case.keys():
                    com = self.write_command(f'{self.sequence_id}{seq_id}', case)
                    self.subcomponents[f'{self.sequence_id}{seq_id}'] = com
                    seq_id += 1
                else:
                    raise SequenceTreeError(Exception)


class Command(AbstractSequence):

    def __init__(self, command_id: str, sequence_dict: Dict[Any, Any], parent: 'Sequence' or 'NightPlan') -> None:
        self.command_id = command_id
        self.sequence_dict = sequence_dict
        self.parent = parent
        self.args = self.build_args(self.sequence_dict)
        self.kwargs = self.build_kwargs(self.sequence_dict)
        self.parent_args = self.parent.args + self.parent.parent_args
        self.parent_kwargs = self.parent.kwargs | self.parent.parent_kwargs
        self.command_name = self.sequence_dict['command_name']
        self.subcomponents = {}
        self.priority: int = 0
        super().__init__(self)
        self.write_subcommands()


    def write_subcommands(self):

        if self.command_name == 'OBJECT':
            id = 0
            if len(self.args) == 2:
                ra = self.args[0]
                dec = self.args[1]
            else:
                ra = self.args[1]
                dec = self.args[2]
            sub = MountSlewCooSync(self.command_id+str(id), self, ra=ra, dec=dec)
            self.subcomponents[self.command_id+str(id)] = sub
            id += 1
            sub = DomeSlaveTelescope(self.command_id + str(id), self)
            self.subcomponents[self.command_id + str(id)] = sub
            id += 1
            if 'seq' in self.kwargs:
                seq_list = list(self.kwargs['seq'].split(','))
                for n in seq_list:
                    par = list(n.split('/'))
                    sub = ChangeFilter(self.command_id + str(id), self, filter=par[1])
                    self.subcomponents[self.command_id + str(id)] = sub
                    id += 1
                    sub = CameraExposure(self.command_id + str(id), self, exp_no=par[0], exp_time=par[2])
                    self.subcomponents[self.command_id + str(id)] = sub
                    id += 1

    def run(self):
        pass


class SubCommand:

    def __init__(self, id: str, parent: 'Command', **kwargs) -> None:
        self.id = id
        self.parent = parent
        self.done: bool = False
        self.priority: int = 0
        self.args = []
        self.kwargs = kwargs
        super().__init__()
        logger.info(f'Subcommand {id} is written')


class ChangeFilter(SubCommand):
    pass

class MountSlewCooSync(SubCommand):
    pass

class DomeSlaveTelescope(SubCommand):
    pass

class CameraExposure(SubCommand):
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
        # TODO keep nightplans in settings, only load plans for night, else delete from memory.

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




input_1 = """BEGINSEQUENCE ak=6
               OBJECT FF_Aql 18:58:14.75 17:21:39.29 seq=5/I/60,5/V/70
               BEGINSEQUENCE focus=+30
                   OBJECT V496_Aql 19:08:20.77 -07:26:15.89 seq=1/V/20
                   OBJECT V496_Aql 19:08:20.77 -07:26:15.89 seq=1/V/20
               ENDSEQUENCE
           ENDSEQUENCE
           """
input_2 = """
            BEGINSEQUENCE x y z execute_at_time=16:00
                ZERO seq=15/I/0
                DARK seq=10/V/300,10/I/200
                BEGINSEQUENCE abc=13
                    DOMEFLAT seq=7/V/20,7/I/20
                    BEGINSEQUENCE
                        DOMEFLAT seq=10/str_u/100 domeflat_lamp=0.7
                    ENDSEQUENCE
                ENDSEQUENCE
                OBJECT FF_Aql 18:58:14.75 17:21:39.29 seq=2/I/60,2/V/70
            ENDSEQUENCE

            BEGINSEQUENCE execute_periodically=02:00 priority=+10
                FOCUS NG31 12:12:12 20:20:20
            ENDSEQUENCE
            """


pr = PlanRunner('DefaultClient', 'Observ_plan_1')
pr.load_night_plan_string('112232322', input_1)
#pr.load_night_plan_string('112232333', input_2)
#pr.load_night_plan_string('112232322', input, overwrite=True)
#pr.run_night('112232322')

def fuu(j, k):
    if isinstance(k, Command):
        # print(j, k, k.args, k.kwargs, k.parent_args, k.parent_kwargs)
        pass
    if isinstance(k, Sequence):
        pass
    else:
        if isinstance(k, SubCommand):
            print(j, k, k.args, k.kwargs)




x = pr.observation_plan.subcomponents
for h in x.keys():
    fuu(h, x[h])
    y = x[h].subcomponents
    for j in y.keys():
        fuu(j, y[j])
        z = y[j].subcomponents
        for t in z.keys():
            fuu(t, z[t])
            if isinstance(z[t], Sequence) or isinstance(z[t], Command):
                f = z[t].subcomponents
                for o in f.keys():
                    fuu(o, f[o])
                    if isinstance(f[o], Sequence) or isinstance(f[o], Command):
                        a = f[o].subcomponents
                        for b in a.keys():
                            fuu(b, a[b])
                            if isinstance(a[b], Sequence) or isinstance(a[b], Command):
                                c = a[b].subcomponents
                                for d in c.keys():
                                    fuu(d, c[d])
                                    if isinstance(c[d], Sequence) or isinstance(c[d], Command):
                                        e = c[d].subcomponents
