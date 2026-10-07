import { z } from "zod";

export const simpleCareTeamMessageSchema = z.object({
  id: z.string(),
  sender: z.enum(["patient", "staff"]),
  content: z.string(),
  created_at: z.string(),
  read_at: z.string().nullable(),
});

export const simpleCareTeamThreadSchema = z.object({
  session_id: z.string(),
  unread_from_staff: z.number(),
  messages: z.array(simpleCareTeamMessageSchema),
});

export const simpleStaffConversationSchema = z.object({
  session_id: z.string(),
  unread_from_staff: z.number(),
});

export const simpleCaseMessagesSchema = z.object({
  session_id: z.string(),
  unread_count: z.number(),
  messages: z.array(simpleCareTeamMessageSchema),
});
