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
        // Map the data to ensure compatibility with new format
        const processedData = data.map(item => ({
          // Support both "name" and "model" fields for backwards compatibility
          model: item.name || item.model,
          productionScore: item.productionScore || 0,
          milestones: item.milestones || 0,
          automationMilestones: item['automation-milestones'] || 0,
          labTasksSuccessRate: item.labTasksSuccessRate || 0,
          labTasksCompleted: item.labTasksCompleted || 0, // For backward compatibility
          mostComplexItem: item.mostComplexItem || 'none',
          submittedBy: item.submittedBy || 'Unknown',
          submissionDate: item.submissionDate || 'Unknown',
          verified: item.verified || false,
          url: item.url || null
        }));

        setModelData(processedData);
        setActiveModels(processedData.map(d => d.model));
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

  // Format submission date
  const formatDate = (dateString) => {
    if (!dateString || dateString === 'Unknown') return 'Unknown';
    try {
      const date = new Date(dateString);
      return date.toLocaleDateString();
    } catch (e) {
      return dateString;
    }
  };

  // Render model name with optional URL
  const renderModelName = (model, url) => {
    if (url) {
      return (
        <a
          href={url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-factorio-highlight hover:text-factorio-accent underline"
        >
          {model}
        </a>
      );
    }
    return model;
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
        <h3 className="text-lg font-medium mb-2">Milestone Comparison</h3>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={sortedData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="model" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Bar dataKey="milestones" fill="#82ca9d" name="Total Milestones" />
              <Bar dataKey="automationMilestones" fill="#ff9d00" name="Automation Milestones" />
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
              <Line type="monotone" dataKey="labTasksSuccessRate" stroke="#ff9d00" name="Lab Success Rate (%)" />
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
                onClick={() => handleSort('automationMilestones')}
              >
                Automation {sortField === 'automationMilestones' && (sortDirection === 'asc' ? '↑' : '↓')}
              </th>
              <th
                className="py-2 px-4 border-b text-left cursor-pointer hover:bg-gray-200"
                onClick={() => handleSort('labTasksSuccessRate')}
              >
                Lab Success % {sortField === 'labTasksSuccessRate' && (sortDirection === 'asc' ? '↑' : '↓')}
              </th>
              <th className="py-2 px-4 border-b text-left">Most Complex Item</th>
              <th className="py-2 px-4 border-b text-left">Submitted By</th>
              <th className="py-2 px-4 border-b text-left">Date</th>
            </tr>
          </thead>

          <tbody>
            {sortedData.map((item, index) => (
              <tr key={item.model} className={index % 2 === 0 ? 'bg-gray-50' : 'bg-white'}>
                <td className="py-2 px-4 border-b">{index + 1}</td>
                <td className="py-2 px-4 border-b font-medium">
                  {renderModelName(item.model, item.url)}
                  {item.verified && <span className="ml-2 text-green-600" title="Verified">✓</span>}
                </td>
                <td className="py-2 px-4 border-b">{item.productionScore.toLocaleString()}</td>
                <td className="py-2 px-4 border-b">{item.milestones}</td>
                <td className="py-2 px-4 border-b">{item.automationMilestones}</td>
                <td className="py-2 px-4 border-b">{item.labTasksSuccessRate}%</td>
                <td className="py-2 px-4 border-b">{item.mostComplexItem}</td>
                <td className="py-2 px-4 border-b">{item.submittedBy}</td>
                <td className="py-2 px-4 border-b">{formatDate(item.submissionDate)}</td>
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