import { existsSync, mkdirSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const frontendDir = path.resolve(__dirname, '..');
const repoRoot = path.resolve(frontendDir, '..');
const backendDir = path.join(repoRoot, 'backend');
const schemaPath = path.join(frontendDir, 'openapi', 'openapi.json');
const generatedDir = path.join(frontendDir, 'src', 'lib', 'api', 'generated');
const requestTemplatePath = path.join(frontendDir, 'openapi', 'request.ts');
const args = new Set(process.argv.slice(2));

if (args.has('--schema-only') && args.has('--client-only')) {
  console.error('Cannot use --schema-only and --client-only together.');
  process.exit(1);
}

const run = (command, commandArgs, options = {}) => {
  const result = spawnSync(command, commandArgs, {
    cwd: options.cwd ?? frontendDir,
    stdio: 'inherit',
    env: { ...process.env, ...options.env },
  });

  if (result.error) throw result.error;
  if (result.status !== 0) process.exit(result.status ?? 1);
};

const canRun = (command, commandArgs = []) => {
  const result = spawnSync(command, commandArgs, {
    cwd: frontendDir,
    stdio: 'ignore',
    env: process.env,
  });
  return result.status === 0;
};

const resolvePython = () => {
  const candidates = [
    path.join(repoRoot, '.venv', 'bin', 'python'),
    path.join(backendDir, '.venv', 'bin', 'python'),
    process.env.PYTHON_BIN,
    'python3',
  ].filter(Boolean);

  for (const candidate of candidates) {
    if (canRun(candidate, ['--version'])) {
      return candidate;
    }
  }

  throw new Error('No Python interpreter available for OpenAPI export.');
};

const resolveOpenApiCli = () => {
  const cli = path.join(frontendDir, 'node_modules', '.bin', 'openapi');
  if (!existsSync(cli)) {
    throw new Error('openapi CLI not found. Run `corepack pnpm install --dir frontend` first.');
  }
  return cli;
};

mkdirSync(path.dirname(schemaPath), { recursive: true });
mkdirSync(generatedDir, { recursive: true });

const python = resolvePython();
const openapiCli = resolveOpenApiCli();
const schemaOnly = args.has('--schema-only');
const clientOnly = args.has('--client-only');

if (!clientOnly) {
  run(
    python,
    ['manage.py', 'export_openapi', '--output', schemaPath, '--path-prefix', '/api/'],
    {
      cwd: backendDir,
      env: { SECRET_KEY: process.env.SECRET_KEY || 'openapi-export-local' },
    }
  );
}

if (!schemaOnly) {
  run(openapiCli, [
    '--input',
    'openapi/openapi.json',
    '--output',
    'src/lib/api/generated',
    '--client',
    'axios',
    '--request',
    path.relative(frontendDir, requestTemplatePath),
  ]);
}

console.log(`OpenAPI schema: ${path.relative(repoRoot, schemaPath)}`);
console.log(`Generated client: ${path.relative(repoRoot, generatedDir)}`);
