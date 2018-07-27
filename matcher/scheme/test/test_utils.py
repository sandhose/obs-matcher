from unittest.mock import Mock, call

from pytest import raises

from matcher.exceptions import InvalidTransition
from matcher.scheme.utils import CustomEnum, Transition, after, before


class TestCustomEnum():
    def test_transitions(self):
        class TestEnum(CustomEnum):
            SCHEDULED = 1
            RUNNING = 2
            SUCCESS = 3
            FAILED = 4

            __transitions__ = [
                Transition('schedule', [FAILED, None], SCHEDULED),
                Transition('run', [SCHEDULED], RUNNING),
                Transition('success', [RUNNING], SUCCESS),
                Transition('fail', [RUNNING], FAILED),
            ]

        @TestEnum.act_as_statemachine('my_state')
        class TestMachine(object):
            my_state = None

        machine = TestMachine()

        with raises(InvalidTransition):
            machine.run()

        machine.schedule()
        assert machine.my_state == TestEnum.SCHEDULED
        machine.run()
        assert machine.my_state == TestEnum.RUNNING
        machine.fail()
        assert machine.my_state == TestEnum.FAILED

        with raises(InvalidTransition):
            machine.run()

        machine.schedule().run().success()
        assert machine.my_state == TestEnum.SUCCESS

    def test_can_apply(self):
        class State(CustomEnum):
            NOT_STARTED = 1
            RUNNING = 2
            STOPPED = 3
            FINISHED = 4

            __transitions__ = [
                Transition('run', [NOT_STARTED], RUNNING),
                Transition('stop', [RUNNING], STOPPED),
                Transition('finish', [RUNNING], FINISHED),
                Transition('restart', [STOPPED, FINISHED], RUNNING),
            ]

        @State.act_as_statemachine
        class TestMachine(object):
            state = State.NOT_STARTED

        machine = TestMachine()

        assert machine.state == State.NOT_STARTED
        assert machine.is_not_started
        assert machine.can_run
        assert not machine.can_stop
        assert not machine.can_finish
        assert not machine.can_restart

        machine.run()
        assert machine.state == State.RUNNING
        assert machine.is_running
        assert not machine.can_run
        assert machine.can_stop
        assert machine.can_finish
        assert not machine.can_restart

        machine.stop()
        assert machine.state == State.STOPPED
        assert machine.is_stopped
        assert not machine.can_run
        assert not machine.can_stop
        assert not machine.can_finish
        assert machine.can_restart

        machine.restart()
        assert machine.state == State.RUNNING
        assert machine.is_running
        assert not machine.can_run
        assert machine.can_stop
        assert machine.can_finish
        assert not machine.can_restart

        machine.finish()
        assert machine.state == State.FINISHED
        assert machine.is_finished
        assert not machine.can_run
        assert not machine.can_stop
        assert not machine.can_finish
        assert machine.can_restart

    def test_is_state(self):
        class TestEnum(CustomEnum):
            FIRST = 1
            SECOND = 2
            THIRD = 3

            __transitions__ = [
                Transition('first', [None], FIRST)
            ]

        @TestEnum.act_as_statemachine
        class TestMachine(object):
            state = TestEnum.FIRST

        machine = TestMachine()

        assert machine.is_first
        assert not machine.is_second
        assert not machine.is_third

        machine.state = TestEnum.SECOND
        assert not machine.is_first
        assert machine.is_second
        assert not machine.is_third

        machine.state = TestEnum.THIRD
        assert not machine.is_first
        assert not machine.is_second
        assert machine.is_third

        machine.state = None
        assert not machine.is_first
        assert not machine.is_second
        assert not machine.is_third

    def test_hooks(self):
        class TestEnum(CustomEnum):
            FIRST_STATE = 1
            SECOND_STATE = 2

            __transitions__ = [
                Transition('first', [SECOND_STATE], FIRST_STATE),
                Transition('second', [FIRST_STATE], SECOND_STATE),
            ]

        parent = Mock()
        parent.before_each = Mock()
        parent.after_each = Mock()
        parent.before_first = Mock()
        parent.after_first = Mock()
        parent.before_second = Mock()
        parent.after_second = Mock()

        @TestEnum.act_as_statemachine
        class TestMachine(object):
            state = TestEnum.SECOND_STATE

            before_each = before(parent.before_each)
            after_each = after(parent.after_each)
            before_first = before('first')(parent.before_first)
            after_first = after('first')(parent.after_first)
            before_second = before('second')(parent.before_second)
            after_second = after('second')(parent.after_second)

        machine = TestMachine()
        machine.first()
        machine.second('arg', key='value')

        assert parent.mock_calls == [
            call.before_each(machine),
            call.before_first(machine),
            call.after_each(machine),
            call.after_first(machine),
            call.before_each(machine, 'arg', key='value'),
            call.before_second(machine, 'arg', key='value'),
            call.after_each(machine, 'arg', key='value'),
            call.after_second(machine, 'arg', key='value'),
        ]

    def test_hook_return(self):
        class TestEnum(CustomEnum):
            FIRST_STATE = 1
            SECOND_STATE = 2
            THIRD_STATE = 2

            __transitions__ = [
                Transition('first', [SECOND_STATE, None], FIRST_STATE),
                Transition('second', [FIRST_STATE], SECOND_STATE),
                Transition('third', [FIRST_STATE, SECOND_STATE], THIRD_STATE),
            ]

        parent = Mock()
        parent.before_each = Mock(return_value=True)
        parent.after_each = Mock(return_value=True)
        parent.before_first = Mock(return_value=True)
        parent.after_first = Mock(return_value=True)
        parent.before_second = Mock(return_value=False)
        parent.after_second = Mock(return_value=True)
        parent.before_third = Mock(return_value=True)
        parent.after_third = Mock(return_value=False)
        parent.before_each_prime = Mock(return_value=True)
        parent.after_each_prime = Mock(return_value=True)

        @TestEnum.act_as_statemachine
        class TestMachine(object):
            state = None

            before_each = before(parent.before_each)
            after_each = after(parent.after_each)
            before_first = before('first')(parent.before_first)
            after_first = after('first')(parent.after_first)
            before_second = before('second')(parent.before_second)
            after_second = after('second')(parent.after_second)
            before_third = before('third')(parent.before_third)
            after_third = after('third')(parent.after_third)
            before_each_prime = before(parent.before_each_prime)
            after_each_prime = after(parent.after_each_prime)

        machine = TestMachine()
        machine.first()  # Should not fail
        assert machine.state == TestEnum.FIRST_STATE

        with raises(Exception):
            machine.second()  # Should fail before, therefore not change state
        assert machine.state == TestEnum.FIRST_STATE

        with raises(Exception):
            machine.third()  # Should fail after, therefore change the state
        assert machine.state == TestEnum.THIRD_STATE

        assert parent.mock_calls == [
            call.before_each(machine),
            call.before_first(machine),
            call.before_each_prime(machine),
            call.after_each(machine),
            call.after_first(machine),
            call.after_each_prime(machine),

            call.before_each(machine),
            call.before_second(machine),  # Failed on this one

            call.before_each(machine),
            call.before_third(machine),
            call.before_each_prime(machine),
            call.after_each(machine),
            call.after_third(machine),  # Failed on this one
        ]
