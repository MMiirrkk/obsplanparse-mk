from pyaraucaria. import ObsPlanParser

class ObservationPlan:

    def __init__(self, client_name='DefaultClient') -> None:
        self.client_name = client_name
        self.nightplans = {}
        super().__init__()

    def get_nightplan(self, nightplan_id: str):
        try:
            return self.nightplans[nightplan_id]
        except LookupError:
            import NightPlan
            np = NightPlan(nightplan_id, self)
            self.nightplans[nightplan_id] = np
            return np


class NightPlan:

    def __init__(self, id: str, observation_plan: 'ObservationPlan') -> None:
        self.id = id
        self.sequences = {}
        super().__init__(id=id, obervation_plan=observation_plan)

    def get_sequence(self, sequence_id: str):
        try:
            return self.sequences[sequence_id]
        except LookupError:
            import Sequence
            seq = Sequence(sequence_id, self)
            self.sequences[sequence_id] = seq
            return seq




class Sequence:

    def __init__(self, id: str, night_plan: 'NightPlan') -> None:
        self.id = id
        self.commands = {}
        super().__init__(id=id, night_plan=night_plan)

    def get_command(self, command_id: str):
        try:
            return self.commands[command_id]
        except LookupError:
            import Command
            cm = Command(command_id, self)
            self.commands[command_id] = cm
            return cm


class Command:

    def __init__(self, id: str, sequence: 'Sequence') -> None:
        self.id = id
        self.executors = {}
        super().__init__(id=id, sequence=sequence)

    def get_executor(self, executor_id: str):
        try:
            return self.executors[executor_id]
        except LookupError:
            import Executor
            ex = Executor(executor_id, self)
            self.executors[executor_id] = ex
            return ex



class Executor:

    def __init__(self, id: str, command: 'Command') -> None:
        self.id = id
        super().__init__(id=id, command=command)



class ChangeFilter(Executor):
    pass

class MountSlewCooSync(Executor):
    pass

class DomeSlewAz(Executor):
    pass

class CameraExposure(Executor):
    pass


class PlanRunner:

    def __init__(self):
        pass


    input = """
        OBJECT HD193901 20:23:35.8 -21:22:14.0 seq=1/V/300,2/V/500
        """

    output =


