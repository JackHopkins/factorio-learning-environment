const fs = require('fs');
const path = require('path');

const resultsDir = path.join(__dirname, '../../leaderboard/results');
const outputDir = path.join(__dirname, '../../leaderboard/processed');
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

    // Add to combined results
    combinedResults.push(resultData);
  } catch (error) {
    console.error(`Error processing ${file}: ${error.message}`);
  }
});

// Sort by production score
combinedResults.sort((a, b) => b.productionScore - a.productionScore);

// Write combined results to output file
fs.writeFileSync(outputFile, JSON.stringify(combinedResults, null, 2));

console.log(`Processed ${combinedResults.length} result files`);