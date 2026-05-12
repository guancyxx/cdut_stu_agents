---
name: composables
description: "Skill for the Composables area of cdut_stu_agents. 84 symbols across 8 files."
---

# Composables

84 symbols | 8 files | Cohesion: 77%

## When to Use

- Working with code in `frontend-vue-ai-chat/`
- Understanding how sanitizeTextInput, validateLoginPayload, validateRegisterPayload work
- Modifying composables-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `frontend-vue-ai-chat/src/composables/useChatFeature.js` | clearPendingAttachments, clearSuggestions, sendSuggestion, scrollToBottom, encodeAttachmentsAsText (+21) |
| `frontend-vue-ai-chat/src/composables/useOjAuthAndProblems.js` | getStoredLastUsername, persistLastUsername, resolveUserProfile, useOjAuthAndProblems, resetAuthError (+20) |
| `frontend-vue-ai-chat/src/composables/useSessions.js` | createTimeLabel, appendMessageToSession, useSessions, createSessionEntity, saveSessions (+9) |
| `frontend-vue-ai-chat/src/composables/useChatSocket.js` | waitForOpen, sendQuery, useChatSocket, getWsUrl, resetStreamState (+1) |
| `frontend-vue-ai-chat/src/utils/validators.js` | sanitizeTextInput, validateLoginPayload, validateRegisterPayload, validateChatInput, validateDifficulty |
| `frontend-vue-ai-chat/src/services/apiClient.js` | createApiClient, fetchProfile, fetchCaptcha, fetchTestCaseContent, reportSubmissionFallback |
| `frontend-vue-ai-chat/src/services/csrfService.js` | readCookie, ensureCsrfToken |
| `frontend-vue-ai-chat/src/utils/agents.js` | getAgentInfo |

## Entry Points

Start here when exploring this area:

- **`sanitizeTextInput`** (Function) — `frontend-vue-ai-chat/src/utils/validators.js:10`
- **`validateLoginPayload`** (Function) — `frontend-vue-ai-chat/src/utils/validators.js:23`
- **`validateRegisterPayload`** (Function) — `frontend-vue-ai-chat/src/utils/validators.js:44`
- **`readCookie`** (Function) — `frontend-vue-ai-chat/src/services/csrfService.js:0`
- **`ensureCsrfToken`** (Function) — `frontend-vue-ai-chat/src/services/csrfService.js:5`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `sanitizeTextInput` | Function | `frontend-vue-ai-chat/src/utils/validators.js` | 10 |
| `validateLoginPayload` | Function | `frontend-vue-ai-chat/src/utils/validators.js` | 23 |
| `validateRegisterPayload` | Function | `frontend-vue-ai-chat/src/utils/validators.js` | 44 |
| `readCookie` | Function | `frontend-vue-ai-chat/src/services/csrfService.js` | 0 |
| `ensureCsrfToken` | Function | `frontend-vue-ai-chat/src/services/csrfService.js` | 5 |
| `createApiClient` | Function | `frontend-vue-ai-chat/src/services/apiClient.js` | 0 |
| `fetchProfile` | Function | `frontend-vue-ai-chat/src/services/apiClient.js` | 33 |
| `fetchCaptcha` | Function | `frontend-vue-ai-chat/src/services/apiClient.js` | 35 |
| `useOjAuthAndProblems` | Function | `frontend-vue-ai-chat/src/composables/useOjAuthAndProblems.js` | 61 |
| `resetAuthError` | Function | `frontend-vue-ai-chat/src/composables/useOjAuthAndProblems.js` | 135 |
| `resetUserProfileFields` | Function | `frontend-vue-ai-chat/src/composables/useOjAuthAndProblems.js` | 139 |
| `refreshCaptcha` | Function | `frontend-vue-ai-chat/src/composables/useOjAuthAndProblems.js` | 146 |
| `applyLoginSuccess` | Function | `frontend-vue-ai-chat/src/composables/useOjAuthAndProblems.js` | 156 |
| `applyUserProfileData` | Function | `frontend-vue-ai-chat/src/composables/useOjAuthAndProblems.js` | 172 |
| `fetchUserProfile` | Function | `frontend-vue-ai-chat/src/composables/useOjAuthAndProblems.js` | 185 |
| `hydrateAuthSession` | Function | `frontend-vue-ai-chat/src/composables/useOjAuthAndProblems.js` | 197 |
| `login` | Function | `frontend-vue-ai-chat/src/composables/useOjAuthAndProblems.js` | 214 |
| `register` | Function | `frontend-vue-ai-chat/src/composables/useOjAuthAndProblems.js` | 241 |
| `clearAuthState` | Function | `frontend-vue-ai-chat/src/composables/useOjAuthAndProblems.js` | 269 |
| `logout` | Function | `frontend-vue-ai-chat/src/composables/useOjAuthAndProblems.js` | 279 |

## Execution Flows

| Flow | Type | Steps |
|------|------|-------|
| `HydrateAuthSession → SanitizeTextInput` | intra_community | 6 |
| `SelectOrCreateProblemSession → CreateHistoryStorageKey` | cross_community | 5 |
| `SelectOrCreateProblemSession → SanitizeStoredMessage` | cross_community | 5 |
| `SelectOrCreateProblemSession → GetSessionById` | cross_community | 5 |
| `SendProblemContextToAi → GetSessionById` | cross_community | 5 |
| `SendProblemContextToAi → SaveSessions` | cross_community | 5 |
| `SendSuggestion → SanitizeStoredMessage` | cross_community | 4 |
| `SendSuggestion → CreateHistoryStorageKey` | cross_community | 4 |
| `SubmitSolution → RequestJson` | cross_community | 4 |
| `Register → SanitizeTextInput` | intra_community | 4 |

## Connected Areas

| Area | Connections |
|------|-------------|
| Services | 5 calls |

## How to Explore

1. `gitnexus_context({name: "sanitizeTextInput"})` — see callers and callees
2. `gitnexus_query({query: "composables"})` — find related execution flows
3. Read key files listed above for implementation details
