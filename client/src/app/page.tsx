import { Chat } from "@/components/chat";

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-4 sm:p-6 md:p-8 bg-muted/30">
      <div className="w-full h-[calc(100vh-2rem)] sm:h-[calc(100vh-3rem)] md:h-[calc(100vh-4rem)] max-h-[800px]">
        <Chat />
      </div>
    </main>
  );
}
