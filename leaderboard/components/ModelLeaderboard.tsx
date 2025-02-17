'use client';

import { useEffect, useState } from 'react';
import type { ModelStats } from '@/lib/db';
import { ChevronDown, ChevronUp, Minus } from 'lucide-react';

export default function ModelLeaderboard() {
    const [leaderboardData, setLeaderboardData] = useState<ModelStats[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const fetchData = async () => {
            try {
                const response = await fetch('/api/leaderboard');
                if (!response.ok) {
                    throw new Error('Failed to fetch leaderboard data');
                }
                const data = await response.json();
                setLeaderboardData(data);
                setLoading(false);
            } catch (err) {
                setError(err instanceof Error ? err.message : 'An error occurred');
                setLoading(false);
            }
        };

        fetchData();
    }, []);

    const getScoreIndicator = (index: number) => {
        if (index === 0) return <ChevronUp className="text-green-500" />;
        if (index === leaderboardData.length - 1) return <ChevronDown className="text-red-500" />;
        return <Minus className="text-gray-500" />;
    };

    if (loading) {
        return (
            <div className="w-full max-w-4xl mx-auto p-8 text-center">
                Loading leaderboard data...
            </div>
        );
    }

    if (error) {
        return (
            <div className="w-full max-w-4xl mx-auto p-8 text-center text-red-500">
                Error: {error}
            </div>
        );
    }

    return (
        <div className="w-full max-w-4xl mx-auto p-4">
            <h1 className="text-2xl font-bold mb-6">Model Leaderboard</h1>
            <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                    <thead className="bg-gray-50 dark:bg-gray-800">
                    <tr>
                        <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                            Rank
                        </th>
                        <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                            Model
                        </th>
                        <th scope="col" className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                            Mean Score
                        </th>
                        <th scope="col" className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                            Cumulative Score
                        </th>
                    </tr>
                    </thead>
                    <tbody className="bg-white dark:bg-gray-900 divide-y divide-gray-200 dark:divide-gray-700">
                    {leaderboardData.map((model, index) => (
                        <tr key={model.id} className="hover:bg-gray-50 dark:hover:bg-gray-800">
                            <td className="px-6 py-4 whitespace-nowrap">
                                <div className="flex items-center gap-2">
                                    {index + 1}
                                    {getScoreIndicator(index)}
                                </div>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap font-mono">
                                {model.model_name}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-right">
                                {model.mean_score.toFixed(3)}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-right font-semibold">
                                {model.cumulative_score.toLocaleString(undefined, {
                                    minimumFractionDigits: 0,
                                    maximumFractionDigits: 0
                                })}
                            </td>
                        </tr>
                    ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
}