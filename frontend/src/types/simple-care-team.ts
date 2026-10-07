/**
 * Shared DTOs for the simple_agent care-team chat pilot -- used by both the
 * patient side (`/api/v1/simple-triage/chat/{id}/*`) and the nurse side
 * (`/api/v1/nurse-simple/cases/{id}/*`). Both routers return the exact same
 * message shape, so one type/schema pair covers both.
 */

export interface SimpleCareTeamMessageDTO {
  id: string;
  sender: "patient" | "staff";
  content: string;
  created_at: string;
  read_at: string | null;
}

/** Patient-side thread response (`unread_from_staff`). */
export interface SimpleCareTeamThreadDTO {
  session_id: string;
  unread_from_staff: number;
  messages: SimpleCareTeamMessageDTO[];
}

/** Patient-side send/mark-read response (no message list). */
export interface SimpleStaffConversationDTO {
  session_id: string;
  unread_from_staff: number;
}

/** Nurse-side thread response (`unread_count` = unread from the patient). */
export interface SimpleCaseMessagesDTO {
  session_id: string;
  unread_count: number;
  messages: SimpleCareTeamMessageDTO[];
}
