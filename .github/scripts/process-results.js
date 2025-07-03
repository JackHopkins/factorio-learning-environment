const fs = require('fs');
const path = require('path');

const resultsDir = path.join(__dirname, '../../docs/leaderboard/results');
const outputDir = path.join(__dirname, '../../docs/leaderboard/processed');
const outputFile = path.join(outputDir, 'combined-results.json');

// Create the output directory if it doesn't exist
if (!fs.existsSync(outputDir)) {
  fs.mkdirSync(outputDir, { recursive: true });
}

// Read all JSON files in the results directory
const resultFiles = fs.readdirSync(resultsDir).filter(file => file.endsWith('.json'));

// Process each file
const combinedResults = [];
resultFiles.forEach(file => {
  const filePath = path.join(resultsDir, file);
  const fileContent = fs.readFileSync(filePath, 'utf8');

  try {
    const resultData = JSON.parse(fileContent);

    // Add verification status based on file location
    const isVerified = process.env.GITHUB_REF === 'refs/heads/main';
    resultData.verified = isVerified;

    // Ensure compatibility with both old and new formats
    const processedData = {
      // Use name field as primary, fall back to model field if name is not present
      model: resultData.name || resultData.model,

      // Production score
      productionScore: resultData.productionScore || 0,

      // Milestones
      milestones: resultData.milestones || 0,

      // Handle "automation-milestones" with dash or camelCase
      automationMilestones: resultData['automation-milestones'] || resultData.automationMilestones || 0,

      // Lab tasks - support both labTasksCompleted (old) and labTasksSuccessRate (new)
      labTasksCompleted: resultData.labTasksCompleted || 0,
      labTasksSuccessRate: resultData.labTasksSuccessRate || 0,

      // Additional metadata
      mostComplexItem: resultData.mostComplexItem || 'none',
      submittedBy: resultData.submittedBy || 'Unknown',
      submissionDate: resultData.submissionDate || new Date().toISOString().split('T')[0],
      url: resultData.url || null,
      verified: isVerified
    };

    // Add to combined results
    combinedResults.push(processedData);
  } catch (error) {
    console.error(`Error processing ${file}: ${error.message}`);
  }
});

// Sort by production score
combinedResults.sort((a, b) => b.productionScore - a.productionScore);

// Write combined results to output file
fs.writeFileSync(outputFile, JSON.stringify(combinedResults, null, 2));

console.log(`Processed ${combinedResults.length} result files`);