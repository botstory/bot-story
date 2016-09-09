from . import location
from ... import matchers, story
from ...story import clear, match_message
from ...utils import answer, build_fake_user, SimpleTrigger


def teardown_function(function):
    print('tear down!')
    clear()


def test_should_trigger_on_any_location():
    trigger = SimpleTrigger()
    user = build_fake_user()

    @story.on(receive=location.Any())
    def one_story():
        @story.then()
        def then(message):
            trigger.passed()

    match_message({
        'location': {
            'lat': 1,
            'lng': 1,
        },
        'user': user,
    })
    assert trigger.is_triggered


def test_should_not_react_on_common_message():
    trigger = SimpleTrigger()
    user = build_fake_user()

    @story.on(receive=location.Any())
    def one_story():
        @story.then()
        def then(message):
            trigger.passed()

    answer.pure_text('Hey!', user)

    assert not trigger.is_triggered


def test_serialize_location():
    m_old = location.Any()
    m_new = matchers.deserialize(matchers.serialize(m_old))
    assert isinstance(m_new, location.Any)