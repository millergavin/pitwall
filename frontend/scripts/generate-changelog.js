import { execSync } from 'child_process';
import { writeFileSync } from 'fs';
import { dirname, join } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));

// Get the last 20 commits
const gitLog = execSync(
  'git log --pretty=format:\'{"hash": "%h", "date": "%ad", "message": "%s", "author": "%an"}\' --date=short -20',
  { encoding: 'utf-8', cwd: join(__dirname, '..', '..') }
);

const commits = gitLog
  .split('\n')
  .filter(line => line.trim())
  .map(line => {
    try {
      return JSON.parse(line);
    } catch {
      return null;
    }
  })
  .filter(Boolean);

const changelog = {
  generated: new Date().toISOString(),
  commits,
};

writeFileSync(
  join(__dirname, '..', 'public', 'changelog.json'),
  JSON.stringify(changelog, null, 2)
);

console.log(`✓ Generated changelog with ${commits.length} commits`);


