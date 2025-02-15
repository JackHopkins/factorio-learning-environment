// app/page.tsx
import ModelLeaderboard from '@/components/ModelLeaderboard';

export default function Home() {
  return (
      <div className="min-h-screen bg-background text-foreground">
        <main className="container mx-auto py-8">
          <ModelLeaderboard />
        </main>
      </div>
  );
}