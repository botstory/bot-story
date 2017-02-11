from botstory import di, matchers
from botstory.ast import callable, forking, stack_utils, story_context
from botstory.integrations import mocktracker

import logging
import inspect

logger = logging.getLogger(__name__)


@di.desc(reg=False)
class StoryProcessor:
    def __init__(self, parser_instance, library):
        self.library = library
        self.parser_instance = parser_instance
        self.tracker = mocktracker.MockTracker()

    @di.inject()
    def add_tracker(self, tracker):
        logger.debug('add_tracker')
        logger.debug(tracker)
        if not tracker:
            return
        self.tracker = tracker

    async def match_message(self, message):
        """

        match bot message to existing stories
        and take into account context of current user

        :param message:
        :return:
        """
        logger.debug('')
        logger.debug('# match_message')
        logger.debug('')
        logger.debug(message)

        self.tracker.new_message(
            user=message and message['user'],
            data=message['data'],
        )

        ctx = story_context.StoryContext(message, self.library)

        if ctx.is_empty_stack():
            if not ctx.does_it_match_any_story():
                # there is no stories for such message
                return None

            ctx = story_context.scope_in(ctx)

            ctx = await self.process_story(ctx)

            ctx = story_context.scope_out(ctx)

        while not ctx.is_waiting_for_input() and not ctx.is_empty_stack():
            logger.debug('# in a loop')
            logger.debug(ctx)

            # looking for first valid matcher
            while True:
                if ctx.is_empty_stack():
                    # we have reach the bottom of stack
                    logger.debug('  we have reach the bottom of stack '
                                 'so no once has receive this message')
                    return None

                if not ctx.is_end_of_story():
                    # if we haven't reach last step in list of story so we can parse result
                    break

                ctx = story_context.scope_out(ctx)

            if ctx.get_child_story():
                ctx = story_context.scope_in(ctx)

            ctx = await self.process_story(ctx)

            ctx = story_context.scope_out(ctx)

        return ctx.waiting_for

    async def process_story(self, ctx):
        logger.debug('')
        logger.debug('# process_story')
        logger.debug('')
        logger.debug(ctx)

        compiled_story = ctx.compiled_story()

        current_story = ctx.message['session']['stack'][-1]
        start_step = current_story['step']
        step = start_step

        # integrate over parts of story
        for step, story_part in enumerate(compiled_story.story_line[start_step:], start_step):
            logger.debug('# in a loop')
            logger.debug(ctx)

            # TODO: don't mutate! should use reducer instead
            current_story['step'] = step

            self.tracker.story(
                user=ctx.user(),
                story_name=ctx.stack()[-1]['topic'],
                story_part_name=story_part.__name__,
            )

            # check whether it could be new scope
            # TODO: it could be done at StoryPartFork.__call__
            if isinstance(story_part, forking.StoryPartFork):
                child_story = None

                if isinstance(ctx.waiting_for, forking.SwitchOnValue):
                    child_story = story_part.get_child_by_validation_result(ctx.waiting_for.value)

                if child_story:
                    # TODO: don't mutate! should use reducer instead
                    # ctx = story_context.scope_in(ctx)
                    self.build_new_scope(ctx.message['session']['stack'], child_story)

                    ctx = await self.process_story(ctx)

                    # TODO: don't mutate! should use reducer instead
                    # ctx = story_context.scope_out(ctx)
                    self.may_drop_scope(child_story, ctx.message['session']['stack'], ctx.waiting_for)
                    break

            logger.debug('#  going to call: {}'.format(story_part.__name__))

            # TODO: don't mutate! should use reducer instead
            ctx.waiting_for = story_part(ctx.message)

            if inspect.iscoroutinefunction(story_part):
                # TODO: don't mutate! should use reducer instead
                ctx.waiting_for = await ctx.waiting_for

            logger.debug('#  got result {}'.format(ctx.waiting_for))

            if ctx.waiting_for and not isinstance(ctx.waiting_for, forking.SwitchOnValue):
                if isinstance(ctx.waiting_for, callable.EndOfStory):
                    # TODO: don't mutate! should use reducer instead
                    if ctx.message:
                        if isinstance(ctx.waiting_for.data, dict):
                            ctx.message['data'] = {**ctx.message['data'], **ctx.waiting_for.data}
                        else:
                            ctx.message['data'] = ctx.waiting_for.data
                else:
                    # TODO: don't mutate! should use reducer instead
                    current_story['data'] = matchers.serialize(
                        matchers.get_validator(ctx.waiting_for)
                    )
                # should wait for new message income
                break

        # TODO: don't mutate! should use reducer instead
        current_story['step'] = step + 1

        return ctx

    def build_new_scope(self, stack, new_ctx_story):
        """
        - build new scope on the top of stack
        - and current scope will wait for it result

        :param stack:
        :param new_ctx_story:
        :return:
        """
        if len(stack) > 0:
            last_stack_item = stack[-1]
            last_stack_item['step'] += 1
            last_stack_item['data'] = matchers.serialize(callable.WaitForReturn())

        logger.debug('[>] going deeper')
        stack.append(stack_utils.build_empty_stack_item(
            new_ctx_story.topic
        ))

    def may_drop_scope(self, compiled_story, stack, waiting_for):
        # we reach the end of story line
        # so we could collapse previous scope and related stack item
        if stack[-1]['step'] >= len(compiled_story.story_line) - 1 and not waiting_for:
            logger.debug('[<] return')
            stack.pop()
