import {execFileSync} from 'node:child_process';
import {checkReleaseChangelog} from '../node/changelog.mjs';
const args=process.argv.slice(2);
if(args.length>2||(args.length&&args[0]!=='--base'))throw Error('usage: node scripts/check_changelog.mjs [--base FULL_SHA]');
let base=args[1]||process.env.CHANGELOG_BASE;
if(!base||/^0{40}$/.test(base))base=execFileSync('git',['rev-parse','HEAD^'],{encoding:'utf8'}).trim();
const release=checkReleaseChangelog(process.cwd(),base);
console.log('CHANGELOG_OK release='+release.version+' date='+release.date);
