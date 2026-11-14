import { copyFileSync, existsSync, mkdirSync } from 'node:fs'
import { dirname, resolve } from 'node:path'

const candidates = [
  resolve(process.cwd(), '../docs/KOLIBRI_GUIDE.md'),
  resolve(process.cwd(), 'docs/KOLIBRI_GUIDE.md'),
]
const source = candidates.find((candidate) => existsSync(candidate))
if (!source) throw new Error('The Kolibri operations guide is missing from the build context.')

const target = resolve(process.cwd(), 'public/guides/kolibri.md')
mkdirSync(dirname(target), { recursive: true })
copyFileSync(source, target)
