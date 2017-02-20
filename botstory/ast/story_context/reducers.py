from botstory import matchers
from botstory.ast import callable, stack_utils, story_context
import logging
import inspect

logger = logging.getLogger(__name__)


async def execute(ctx):
    """
    execute story part at the current context
    and make one step further

    :param ctx:
    :return:
    """
    tail_depth = len(ctx.stack()) - 1

    story_part = ctx.get_current_story_part()
    logger.debug('# going to call: {}'.format(story_part.__name__))
    waiting_for = story_part(ctx.message)
    logger.debug('# got result {}'.format(waiting_for))
    if inspect.iscoroutinefunction(story_part):
        waiting_for = await waiting_for

    # story part could run callable story and return its context
    if isinstance(waiting_for, story_context.StoryContext):
        # for such cases is very important to know `tail_depth`
        # because story context from callable story already has
        # few stack items above our tail
        ctx = waiting_for.clone()
    else:
        ctx = ctx.clone()
        ctx.waiting_for = waiting_for

    tail_data = ctx.message['session']['stack'][tail_depth]['data']
    if ctx.is_waiting_for_input():
        if isinstance(ctx.waiting_for, callable.EndOfStory):
            if isinstance(ctx.waiting_for.data, dict):
                new_data = {**ctx.message['data'], **ctx.waiting_for.data}
            else:
                new_data = ctx.waiting_for.data
            ctx.message = {
                **ctx.message,
                'data': new_data,
            }
        else:
            logger.debug('# before have modified data at stack')
            tail_data = matchers.serialize(
                matchers.get_validator(ctx.waiting_for)
            )

    ctx.message = modify_stack_in_message(ctx.message,
                                          lambda stack: stack[:tail_depth] +
                                                        [{
                                                            'data': tail_data,
                                                            'step': stack[tail_depth]['step'] + 1,
                                                            'topic': stack[tail_depth]['topic'],
                                                        }] +
                                                        stack[tail_depth + 1:])
    logger.debug('# mutated ctx after execute')
    logger.debug(ctx)
    return ctx


def iterate_storyline(ctx):
    """
    iterate the last storyline from the last visited story part

    :param ctx:
    :return:
    """
    start_step = ctx.current_step()

    logger.debug('# start iterate')
    for step, _ in enumerate(ctx.compiled_story().story_line[start_step:], start_step):
        ctx_child = ctx.clone()

        tail = ctx.stack_tail()

        ctx_child.message = modify_stack_in_message(ctx_child.message,
                                                    lambda stack: stack[:-1] + [{
                                                        'data': tail['data'],
                                                        'step': step,
                                                        'topic': tail['topic'],
                                                    }])

        logger.debug('# [{}] iterate'.format(step))
        logger.debug(ctx_child)

        ctx = yield ctx_child
        logger.debug('get back {}'.format(ctx))


def scope_in(ctx):
    """
    - build new scope on the top of stack
    - and current scope will wait for it result

    :param ctx:
    :return:
    """
    ctx = ctx.clone()

    compiled_story = None
    if not ctx.is_empty_stack():
        compiled_story = ctx.get_child_story()
        ctx.message = modify_stack_in_message(ctx.message,
                                              lambda stack: stack[:-1] + [{
                                                  'data': matchers.serialize(callable.WaitForReturn()),
                                                  'step': stack[-1]['step'] + 1,
                                                  'topic': stack[-1]['topic']
                                              }])
    if not compiled_story:
        compiled_story = ctx.compiled_story()

    logger.debug('# [>] going deeper')
    ctx.message = modify_stack_in_message(ctx.message,
                                          lambda stack: stack + [
                                              stack_utils.build_empty_stack_item(compiled_story.topic)])
    logger.debug(ctx)
    return ctx


def scope_out(ctx):
    """
    drop last stack item if:
     - we have reach the end of stack
     - and don't wait any input

    :param ctx:
    :return:
    """
    # we reach the end of story line
    # so we could collapse previous scope and related stack item
    if ctx.is_tail_of_story() and not ctx.could_scope_out():
        logger.debug('# [<] return')
        ctx = ctx.clone()
        ctx.message['session']['stack'] = ctx.message['session']['stack'][:-1]
        logger.debug(ctx)

    return ctx


def modify_stack_in_message(message, mutator):
    return {
        **message,
        'session': {
            **message['session'],
            'stack': mutator(message['session']['stack']),
        }
    }
