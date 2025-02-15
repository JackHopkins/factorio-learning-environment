// app/api/leaderboard/route.ts
import { NextResponse } from 'next/server';
import { getLeaderboardData } from '@/lib/db';

export async function GET() {
    try {
        const data = await getLeaderboardData();
        console.log(data)
        return NextResponse.json(data);
    } catch (error) {
        console.error('Error fetching leaderboard data:', error);
        return NextResponse.json(
            { error: 'Error fetching leaderboard data' },
            { status: 500 }
        );
    }
}