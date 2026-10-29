import { SimplePilotHistoryDetail } from "@/components/chat/SimplePilotHistoryDetail";

interface SimplePilotHistoryDetailPageProps {
  params: Promise<{ id: string }>;
}

export default async function SimplePilotHistoryDetailPage({ params }: SimplePilotHistoryDetailPageProps) {
  const { id } = await params;
  return (
    <div className="h-full w-full overflow-y-auto bg-background">
      <div className="w-full px-4 pb-8 pt-6 sm:px-6">
        <SimplePilotHistoryDetail sessionId={id} />
      </div>
    </div>
  );
}
