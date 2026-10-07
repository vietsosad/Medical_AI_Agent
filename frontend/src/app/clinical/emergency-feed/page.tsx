import { redirect } from "next/navigation";

export default function RemovedEmsRouteRedirect() {
  redirect("/clinical/queue");
}
