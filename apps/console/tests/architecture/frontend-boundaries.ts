import assert from 'node:assert/strict';
import { readFileSync, readdirSync } from 'node:fs';
import path from 'node:path';
import ts from 'typescript';

const root = path.resolve('resources/js');
const manifest = JSON.parse(readFileSync('package.json', 'utf8')) as {
  dependencies: Record<string, string>;
  devDependencies: Record<string, string>;
};
const allowedPackages = new Set([...Object.keys(manifest.dependencies), ...Object.keys(manifest.devDependencies)]);

function checkImport(file: string, specifier: string): string | null {
  if (!specifier.startsWith('.')) {
    const packageName = specifier.startsWith('@') ? specifier.split('/').slice(0, 2).join('/') : specifier.split('/')[0];
    return allowedPackages.has(packageName) ? null : `Unregistered package or alias: ${specifier}`;
  }
  const target = path.resolve(path.dirname(file), specifier);
  if (file === path.join(root, 'app.ts') && target === path.resolve('resources/css/app.css')) return null;
  if (!target.startsWith(`${root}${path.sep}`)) return `Import leaves Console frontend: ${specifier}`;
  const from = path.relative(root, file).split(path.sep);
  const to = path.relative(root, target).split(path.sep);
  if (from[0] === 'shared' && ['contexts', 'pages', 'journeys', 'app'].includes(to[0])) return 'Shared code cannot import application presentation';
  if (to[0] === 'contexts') {
    const sameContext = from[0] === 'contexts' && from[1] === to[1];
    if (!sameContext && to.length > 2 && !/^index(?:\.ts)?$/.test(to[2])) return 'Cross-context imports must use the public context interface';
    if (from[0] === 'contexts' && from[1] !== to[1]) return 'Cross-context composition belongs in journeys or pages';
  }
  return null;
}

function inspect(file: string, source: string): string[] {
  const errors: string[] = [];
  const sourceFile = ts.createSourceFile(file, source, ts.ScriptTarget.Latest, true, ts.ScriptKind.TS);
  function visit(node: ts.Node): void {
    let specifier: ts.Expression | undefined;
    if (ts.isImportDeclaration(node) || ts.isExportDeclaration(node)) specifier = node.moduleSpecifier;
    if (ts.isCallExpression(node) && (node.expression.kind === ts.SyntaxKind.ImportKeyword
        || (ts.isIdentifier(node.expression) && node.expression.text === 'require'))) {
      specifier = node.arguments[0];
      if (!specifier || !ts.isStringLiteral(specifier)) errors.push('Computed module imports are not allowed');
    }
    if (ts.isImportTypeNode(node) && ts.isLiteralTypeNode(node.argument)) specifier = node.argument.literal;
    if (specifier && ts.isStringLiteral(specifier)) {
      const error = checkImport(file, specifier.text);
      if (error) errors.push(error);
    }
    if (ts.isCallExpression(node) && ts.isPropertyAccessExpression(node.expression)
        && node.expression.expression.getText(sourceFile) === 'import.meta'
        && node.expression.name.text.startsWith('glob')) {
      const argument = node.arguments[0];
      if (file !== path.join(root, 'app/bootstrap.ts') || !argument || !ts.isStringLiteral(argument)
          || argument.text !== '../pages/**/*.vue') errors.push('Only the reviewed page resolver glob is allowed');
    }
    ts.forEachChild(node, visit);
  }
  visit(sourceFile);
  return errors;
}

function walk(directory: string): string[] {
  return readdirSync(directory, { withFileTypes: true }).flatMap(entry => {
    const file = path.join(directory, entry.name);
    if (entry.isSymbolicLink()) throw new Error(`Frontend source cannot be a symlink: ${file}`);
    return entry.isDirectory() ? walk(file) : /\.(ts|vue)$/.test(file) ? [file] : [];
  });
}

const fixtures: [string, string, boolean][] = [
  ['pages/Operations.vue', "import x from '../contexts/planning/index'", true],
  ['contexts/planning/features/summary.ts', "import x from './private'", true],
  ['shared/ui/button.ts', "import x from '../../pages/Foundation.vue'", false],
  ['contexts/planning/index.ts', "export { x } from '../inventory/index'", false],
  ['pages/Operations.vue', "import type { X } from '../contexts/planning/features/private'", false],
  ['pages/Operations.vue', "import x from '../../../../services/planning/source'", false],
  ['pages/Operations.vue', "const x = import('../contexts/planning/features/private')", false],
  ['pages/Operations.vue', 'const x = import(variable)', false],
  ['pages/Operations.vue', "import x from '@unregistered/private'", false],
  ['pages/Operations.vue', "const x = import.meta.glob('../../../../services/**')", false],
];
for (const [file, source, valid] of fixtures) assert.equal(inspect(path.join(root, file), source).length === 0, valid, `Boundary fixture: ${file}: ${source}`);

const files = walk(root);
assert.ok(files.length > 0, 'Boundary check must inspect implemented source');
const failures: string[] = [];
for (const file of files) {
  const source = readFileSync(file, 'utf8');
  let scripts = [source];
  if (file.endsWith('.vue')) {
    if (/<script\b[^>]*\bsrc\s*=/.test(source)) failures.push(`${file}: external SFC scripts are not allowed`);
    scripts = [...source.matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/g)].map(match => match[1]);
  }
  for (const script of scripts) failures.push(...inspect(file, script).map(message => `${path.relative(root, file)}: ${message}`));
}
assert.deepEqual(failures, [], failures.join('\n'));
console.log(`Console frontend boundaries: ${files.length} source files; ${fixtures.length} positive/negative fixtures passed.`);
