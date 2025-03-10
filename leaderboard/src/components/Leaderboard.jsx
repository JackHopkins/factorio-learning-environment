// src/components/Leaderboard.jsx
import React, { useState, useEffect, useMemo } from 'react';
import { XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, BarChart, Bar } from 'recharts';

const Leaderboard = () => {
  const [modelData, setModelData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // State for sorting and filtering
  const [sortField, setSortField] = useState('productionScore');
  const [sortDirection, setSortDirection] = useState('desc');
  const [activeModels, setActiveModels] = useState([]);
  const [expandedRows, setExpandedRows] = useState({});

  useEffect(() => {
    const loadData = async () => {
      try {
        // Try to load the JSON data file using window.fs.readFile if available
        let data;
        try {
          // Try to use the window.fs API if available
          const fileContent = await window.fs.readFile('combined-results.json', { encoding: 'utf8' });
          data = JSON.parse(fileContent);
        } catch (fileError) {
          console.warn('Could not load data file directly. Using fallback data:', fileError);
          // Fallback to the sample data if file can't be loaded
          data = [
            {
              "name": "Claude 3.5-Sonnet",
              "productionScore": 293206,
              "milestones": 30,
              "automationMilestones": 13,
              "labTasksSuccessRate": 21.9,
              "mostComplexItem": "plastic-bar",
              "submittedBy": "JackHopkins",
              "submissionDate": "2025-03-06",
              "verified": true
            },
            {
              "name": "Gemini-2-Flash",
              "productionScore": 115782,
              "milestones": 20,
              "automationMilestones": 6,
              "labTasksSuccessRate": 13,
              "mostComplexItem": "iron-gear-wheel",
              "submittedBy": "JackHopkins",
              "submissionDate": "2025-03-07",
              "verified": true
            },
            {
              "name": "GPT4o",
              "productionScore": 87599,
              "milestones": 30,
              "automationMilestones": 9,
              "labTasksSuccessRate": 16.6,
              "mostComplexItem": "plastic-bar",
              "submittedBy": "JackHopkins",
              "submissionDate": "2025-03-07",
              "verified": true
            },
            {
              "name": "Llama-3.3-70b",
              "productionScore": 54998,
              "milestones": 16,
              "automationMilestones": 4,
              "labTasksSuccessRate": 5.2,
              "mostComplexItem": "iron-plate",
              "submittedBy": "JackHopkins",
              "submissionDate": "2025-03-07",
              "verified": true
            },
            {
              "name": "Deepseek-v3",
              "productionScore": 48585,
              "milestones": 22,
              "automationMilestones": 7,
              "labTasksSuccessRate": 15.1,
              "mostComplexItem": "plastic-bar",
              "submittedBy": "JackHopkins",
              "submissionDate": "2025-03-07",
              "verified": true
            },
            {
              "name": "GPT4o-Mini",
              "productionScore": 26756,
              "milestones": 14,
              "automationMilestones": 4,
              "labTasksSuccessRate": 4.2,
              "mostComplexItem": "iron-plate",
              "submittedBy": "JackHopkins",
              "submissionDate": "2025-03-07",
              "verified": true
            }
          ];
        }

        // Process the data
        const processedData = data.map(item => ({
          model: item.name || item.model,
          productionScore: item.productionScore || 0,
          milestones: item.milestones || 0,
          automationMilestones: item.automationMilestones || 0,
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
      } catch (error) {
        console.error("Error loading data:", error);
        setError(error.message);
        setLoading(false);
      }
    };

    loadData();
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

  // Toggle row expansion for details
  const toggleRowExpansion = (model) => {
    setExpandedRows(prev => ({
      ...prev,
      [model]: !prev[model]
    }));
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
        <h2 className="text-2xl font-bold mb-4 text-center">Factory-Bench Leaderboard</h2>

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
                <Bar dataKey="automationMilestones" stackId="a" fill="#ff9d00" name="Automation Milestones" />
                <Bar
                    dataKey="nonAutomationMilestones"
                    stackId="a"
                    fill="#82ca9d"
                    name="Other Milestones"
                    // Calculate non-automation milestones dynamically
                    data={sortedData.map(item => ({
                      ...item,
                      nonAutomationMilestones: item.milestones - item.automationMilestones
                    }))}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="mb-8">
          <h3 className="text-lg font-medium mb-2">Lab Task Comparison</h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={sortedData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="model" />
                <YAxis />
                <Tooltip />
                <Legend />
                <Bar dataKey="labTasksSuccessRate" fill="#8884d8" name="Lab Success Rate (%)" />
              </BarChart>
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
              <th className="py-2 px-4 border-b text-left">Details</th>
            </tr>
            </thead>
            <tbody>
            {sortedData.map((item, index) => (
                <React.Fragment key={item.model}>
                  <tr className={index % 2 === 0 ? 'bg-gray-50' : 'bg-white'}>
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
                    <td className="py-2 px-4 border-b">
                      <button
                          onClick={() => toggleRowExpansion(item.model)}
                          className="bg-gray-200 hover:bg-gray-300 px-3 py-1 rounded text-sm focus:outline-none"
                      >
                        {expandedRows[item.model] ? 'Hide' : 'Show'}
                      </button>
                    </td>
                  </tr>
                  {expandedRows[item.model] && (
                      <tr className={index % 2 === 0 ? 'bg-gray-50' : 'bg-white'}>
                        <td colSpan="8" className="py-2 px-4 border-b">
                          <div className="pl-8">
                            <p><strong>Submitted By:</strong> {item.submittedBy}</p>
                            <p><strong>Date:</strong> {formatDate(item.submissionDate)}</p>
                          </div>
                        </td>
                      </tr>
                  )}
                </React.Fragment>
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