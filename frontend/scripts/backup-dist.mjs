import { cpSync, existsSync, mkdirSync } from 'node:fs';
import { join, resolve } from 'node:path';

const root = resolve(import.meta.dirname, '..');
const dist = join(root, 'dist');
const backups = join(root, 'dist-backups');

if (!existsSync(dist)) {
  console.log('No existing dist folder to back up.');
  process.exit(0);
}

const stamp = new Date().toISOString().replace(/[:.]/g, '-');
const target = join(backups, stamp);
mkdirSync(backups, { recursive: true });
cpSync(dist, target, { recursive: true });
console.log(`Backed up existing dist to ${target}`);
