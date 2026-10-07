import { redirect } from "next/navigation";

export default function RemovedProtocolRouteRedirect() {
  redirect("/clinical/queue");
}
