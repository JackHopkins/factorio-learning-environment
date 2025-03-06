// src/components/Leaderboard.jsx
import React, { useState, useEffect, useMemo } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, BarChart, Bar } from 'recharts';

const Leaderboard = () => {
  const [modelData, setModelData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // State for sorting and filtering
  const [sortField, setSortField] = useState('productionScore');
  const [sortDirection, setSortDirection] = useState('desc');
  const [activeModels, setActiveModels] = useState([]);

  useEffect(() => {
    // Fetch combined results
    fetch('./processed/combined-results.json')
      .then(response => {
        if (!response.ok) {
          throw new Error('Failed to load leaderboard data');
        }
        return response.json();
      })
      .then(data => {
        setModelData(data);
        setActiveModels(data.map(d => d.model));
        setLoading(false);
      })
      .catch(err => {
        setError(err.message);
        setLoading(false);
      });
  }, []);

  // Sort and filter data
  const sortedData = useMemo(() => {
    return [...modelData]
      .filter(item => activeModels.includes(item.model))
      .sort((a, b) => {
        if (sortDirection === 'asc') {
          return a[sortField] - b[sortField];
        } else {
          return b[sortField] - a[sortField];
        }
      });
  }, [sortField, sortDirection, activeModels, modelData]);

  // Toggle sort direction
  const handleSort = (field) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('desc');
    }
  };

  // Toggle model visibility
  const toggleModel = (model) => {
    if (activeModels.includes(model)) {
      setActiveModels(activeModels.filter(m => m !== model));
    } else {
      setActiveModels([...activeModels, model]);
    }
  };

  if (loading) {
    return <div className="text-center p-4">Loading leaderboard data...</div>;
  }

  if (error) {
    return <div className="text-center p-4 text-red-600">Error: {error}</div>;
  }

  return (
    <div className="max-w-4xl mx-auto p-4 bg-white rounded-lg shadow-lg">
      <h2 className="text-2xl font-bold mb-4 text-center">Factorio Learning Environment Leaderboard</h2>

      {/* Model filters */}
      <div className="mb-6">
        <h3 className="text-lg font-medium mb-2">Models</h3>
        <div className="flex flex-wrap gap-2">
          {modelData.map(({ model, verified }) => (
            <button
              key={model}
              onClick={() => toggleModel(model)}
              className={`px-3 py-1 rounded-full text-sm ${
                activeModels.includes(model)
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-200 text-gray-700'
              }`}
            >
              {model} {verified && <span className="ml-1 text-green-300">✓</span>}
            </button>
          ))}
        </div>
      </div>

      {/* Charts */}
      <div className="mb-8">
        <h3 className="text-lg font-medium mb-2">Production Score</h3>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={sortedData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="model" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Bar dataKey="productionScore" fill="#8884d8" name="Production Score" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="mb-8">
        <h3 className="text-lg font-medium mb-2">Log Scale Comparison</h3>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={sortedData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="model" />
              <YAxis scale="log" domain={['auto', 'auto']} />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="productionScore" stroke="#8884d8" name="Production Score" />
              <Line type="monotone" dataKey="milestones" stroke="#82ca9d" name="Milestones" />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="min-w-full bg-white border border-gray-300">
          <thead>
            <tr className="bg-gray-100">
              <th className="py-2 px-4 border-b text-left">Rank</th>
              <th className="py-2 px-4 border-b text-left">Model</th>
              <th
                className="py-2 px-4 border-b text-left cursor-pointer hover:bg-gray-200"
                onClick={() => handleSort('productionScore')}
              >
                Production Score {sortField === 'productionScore' && (sortDirection === 'asc' ? '↑' : '↓')}
              </th>
              <th
                className="py-2 px-4 border-b text-left cursor-pointer hover:bg-gray-200"
                onClick={() => handleSort('milestones')}
              >
                Milestones {sortField === 'milestones' && (sortDirection === 'asc' ? '↑' : '↓')}
              </th>
              <th
                className="py-2 px-4 border-b text-left cursor-pointer hover:bg-gray-200"
                onClick={() => handleSort('labTasksCompleted')}
              >
                Lab Tasks {sortField === 'labTasksCompleted' && (sortDirection === 'asc' ? '↑' : '↓')}
              </th>
              <th className="py-2 px-4 border-b text-left">Most Complex Item</th>
              <th className="py-2 px-4 border-b text-left">Status</th>
            </tr>
          </thead>
          <tbody>
            {sortedData.map((item, index) => (
              <tr key={item.model} className={index % 2 === 0 ? 'bg-gray-50' : 'bg-white'}>
                <td className="py-2 px-4 border-b">{index + 1}</td>
                <td className="py-2 px-4 border-b font-medium">{item.model}</td>
                <td className="py-2 px-4 border-b">{item.productionScore.toLocaleString()}</td>
                <td className="py-2 px-4 border-b">{item.milestones}</td>
                <td className="py-2 px-4 border-b">{item.labTasksCompleted}</td>
                <td className="py-2 px-4 border-b">{item.mostComplexItem}</td>
                <td className="py-2 px-4 border-b">
                  {item.verified ?
                    <span className="text-green-600">✓ Verified</span> :
                    <span className="text-yellow-600">⚠ Pending</span>
                  }
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="mt-4 text-gray-600 text-sm">
        <p>Last updated: {new Date().toLocaleDateString()}</p>
      </div>
    </div>
  );
};

export default Leaderboard;