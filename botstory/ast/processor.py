from botstory import di
from botstory.ast import story_context
from botstory.integrations import mocktracker

import logging

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

            ctx = story_context.reducers.scope_in(ctx)
            ctx = await self.process_story(ctx)
            ctx = story_context.reducers.scope_out(ctx)

        while not ctx.could_scope_out() and not ctx.is_empty_stack():
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

                ctx = story_context.reducers.scope_out(ctx)

            if ctx.has_child_story():
                ctx = story_context.reducers.scope_in(ctx)
            ctx = await self.process_story(ctx)
            ctx = story_context.reducers.scope_out(ctx)

        return ctx.waiting_for

    async def process_story(self, ctx):
        logger.debug('')
        logger.debug('# process_story')
        logger.debug('')
        logger.debug(ctx)

        # integrate over parts of story
        for ctx in story_context.reducers.iterate_through_storyline(ctx):
            logger.debug('# in a loop')
            logger.debug(ctx)

            # TODO: don't mutate! should use reducer instead
            ctx.stack_tail()['step'] = ctx.step

            self.tracker.story(
                user=ctx.user(),
                story_name=ctx.stack()[-1]['topic'],
                story_part_name=ctx.get_current_story_part().__name__,
            )

            if ctx.has_child_story():
                ctx = story_context.reducers.scope_in(ctx)
                ctx = await self.process_story(ctx)
                ctx = story_context.reducers.scope_out(ctx)
                break

            # TODO: don't mutate! should use reducer instead
            ctx.stack_tail()['step'] = ctx.step + 1

            logger.debug('#  going to call: {}'.format(ctx.get_current_story_part().__name__))
            ctx = await story_context.reducers.execute(ctx)
            logger.debug('#  got result {}'.format(ctx.waiting_for))

            if ctx.is_waiting_for_input():
                break

        logger.debug('# return from process_story')
        return ctx
