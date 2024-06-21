from __future__ import annotations

import asyncio

from vocode.streaming.action.abstract_factory import AbstractActionFactory
from vocode.streaming.action.default_factory import DefaultActionFactory
from vocode.streaming.agent.base_agent import ActionResultAgentInput, AgentInput
from vocode.streaming.models.actions import (
    ActionInput,
    TwilioPhoneConversationActionInput,
    VonagePhoneConversationActionInput,
)
from vocode.streaming.utils.state_manager import AbstractConversationStateManager
from vocode.streaming.utils.worker import (
    AbstractWorker,
    InterruptibleEvent,
    InterruptibleEventFactory,
    InterruptibleWorker,
)


class ActionsWorker(InterruptibleWorker):
    consumer: AbstractWorker[InterruptibleEvent[ActionResultAgentInput]]

    def __init__(
        self,
        action_factory: AbstractActionFactory,
        interruptible_event_factory: InterruptibleEventFactory = InterruptibleEventFactory(),
    ):
        super().__init__(
            interruptible_event_factory=interruptible_event_factory,
        )
        self.action_factory = action_factory

    def attach_conversation_state_manager(
        self, conversation_state_manager: AbstractConversationStateManager
    ):
        self.conversation_state_manager = conversation_state_manager

    async def process(self, item: InterruptibleEvent[ActionInput]):
        action_input = item.payload
        action = self.action_factory.create_action(action_input.action_config)
        action.attach_conversation_state_manager(self.conversation_state_manager)
        action_output = await action.run(action_input)
        self.consumer.consume_nonblocking(
            self.interruptible_event_factory.create_interruptible_event(
                ActionResultAgentInput(
                    conversation_id=action_input.conversation_id,
                    action_input=action_input,
                    action_output=action_output,
                    vonage_uuid=(
                        action_input.vonage_uuid
                        if isinstance(action_input, VonagePhoneConversationActionInput)
                        else None
                    ),
                    twilio_sid=(
                        action_input.twilio_sid
                        if isinstance(action_input, TwilioPhoneConversationActionInput)
                        else None
                    ),
                    is_quiet=action.quiet,
                ),
                is_interruptible=False,
            )
        )
