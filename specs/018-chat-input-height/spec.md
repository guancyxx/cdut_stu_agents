# Chat input height increase

## Objective

Increase the bottom chat composer input height to about 1.5x its previous visual height so longer text is easier to edit.

## Scope

In scope:
- Home chat page composer only.
- CSS height tokens for the composer textarea and input row.
- Layout preservation for send button, suggestion chips, trace bar, and pending attachment chips.

Out of scope:
- Message sending logic.
- Session state, dispatch state, attachment data flow, or backend APIs.
- Global textarea sizing for problem/admin/profile forms.

## Current behavior

The chat composer textarea inherits the global textarea `min-height: 72px`. The chat-specific selector only sets width, so the chat page cannot tune composer height independently.

## Desired behavior

The chat composer textarea has a chat-specific height token:
- Minimum visual height: 108px, which is exactly 1.5x the previous 72px baseline.
- Preferred height: clamped to a viewport-based value so common desktop windows get a taller input without overwhelming shorter windows.
- Maximum height: bounded so chat messages and controls remain usable.

## Implementation plan

Open chat page
  -> apply new input area height tokens
  -> verify layout with controls
  -> build and smoke

Implementation notes:
- Add CSS custom properties on `.chat-input-area` for the composer minimum, preferred, and maximum heights.
- Apply `min-height`, `height`, and `max-height` to `.chat-input-area textarea`.
- Keep `.chat-input-row` as a two-column grid so the send button remains aligned beside the textarea.
- Do not modify Vue state or `sendMessage` behavior.

## Acceptance criteria

1. The chat textarea baseline visual height is about 1.5x the previous 72px height.
2. Sending, Enter-to-send, Shift+Enter newline, textarea scrolling/resizing, suggestion chips, trace bar, and pending attachments keep their existing layout contracts.
3. The page has no obvious layout overflow at common desktop widths.
4. The frontend Docker build passes.
