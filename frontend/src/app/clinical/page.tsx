import { redirect } from "next/navigation";

export default function ClinicalPortalRedirect() {
  redirect("/clinical/queue");
}
