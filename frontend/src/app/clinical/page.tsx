import { redirect } from "next/navigation";

import { nurseHomeHref } from "@/lib/agent-mode";

/** `/clinical` dẫn tới đúng màn đầu tiên của điều dưỡng (xem `nurseHomeHref`). */
export default function ClinicalPortalRedirect() {
  redirect(nurseHomeHref());
}
