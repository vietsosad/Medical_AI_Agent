import { redirect } from "next/navigation";

export default function LegacyQueueRedirect() {
  redirect("/clinical/queue");
}
