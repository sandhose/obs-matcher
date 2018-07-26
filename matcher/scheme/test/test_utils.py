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
                Transition('schedule', SCHEDULED, [FAILED, None]),
                Transition('run', RUNNING, [SCHEDULED]),
                Transition('success', SUCCESS, [RUNNING]),
                Transition('fail', FAILED, [RUNNING]),
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

    def test_is_state(self):
        class TestEnum(CustomEnum):
            FIRST = 1
            SECOND = 2
            THIRD = 3

            __transitions__ = [
                Transition('first', FIRST, [None])
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
                Transition('first', FIRST_STATE, [SECOND_STATE]),
                Transition('second', SECOND_STATE, [FIRST_STATE]),
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
        machine.second()

        assert parent.mock_calls == [
            call.before_each(machine),
            call.before_first(machine),
            call.after_each(machine),
            call.after_first(machine),
            call.before_each(machine),
            call.before_second(machine),
            call.after_each(machine),
            call.after_second(machine),
        ]

    def test_hook_return(self):
        class TestEnum(CustomEnum):
            FIRST_STATE = 1
            SECOND_STATE = 2
            THIRD_STATE = 2

            __transitions__ = [
                Transition('first', FIRST_STATE, [SECOND_STATE, None]),
                Transition('second', SECOND_STATE, [FIRST_STATE]),
                Transition('third', THIRD_STATE, [FIRST_STATE, SECOND_STATE]),
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
