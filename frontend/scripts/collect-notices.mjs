import { readFile, readdir, writeFile } from 'node:fs/promises'
import path from 'node:path'

const lock = JSON.parse(await readFile('package-lock.json', 'utf8'))
const sections = [
  'Third-party notices for Digital Himalaya portal\nSee each package for its full terms.\n',
]
for (const [directory, item] of Object.entries(lock.packages)) {
  if (!directory || item.dev) continue
  const info = JSON.parse(await readFile(path.join(directory, 'package.json'), 'utf8'))
  sections.push(
    `\n=== ${info.name} ${info.version} (${item.license ?? info.license ?? 'see package'}) ===\n`,
  )
  const files = await readdir(directory)
  for (const name of files.filter((name) => /^(licen[sc]e|ofl|copying|notice)(\.|$)/i.test(name))) {
    sections.push(await readFile(path.join(directory, name), 'utf8'))
  }
}
await writeFile('dist/THIRD_PARTY_NOTICES.txt', sections.join('\n'))
