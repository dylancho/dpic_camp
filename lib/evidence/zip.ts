import { inflateRawSync } from 'node:zlib';

/**
 * 의존성 없이 단일 파일 ZIP을 푼다. (DART OpenAPI는 corpCode / document를 zip으로 준다)
 * EOCD → central directory → local header 순으로 오프셋을 따라간다.
 */
export function unzipFirstEntry(buf: Buffer): Buffer {
  // End of Central Directory Record (signature 0x06054b50) 를 뒤에서부터 찾는다
  let eocd = -1;
  for (let i = buf.length - 22; i >= 0 && i > buf.length - 22 - 0xffff; i--) {
    if (buf.readUInt32LE(i) === 0x06054b50) {
      eocd = i;
      break;
    }
  }
  if (eocd < 0) throw new Error('ZIP: EOCD를 찾지 못했습니다');

  const cdOffset = buf.readUInt32LE(eocd + 16);
  if (buf.readUInt32LE(cdOffset) !== 0x02014b50) throw new Error('ZIP: central directory 헤더 불일치');

  const method = buf.readUInt16LE(cdOffset + 10);
  const compressedSize = buf.readUInt32LE(cdOffset + 20);
  const localOffset = buf.readUInt32LE(cdOffset + 42);

  if (buf.readUInt32LE(localOffset) !== 0x04034b50) throw new Error('ZIP: local 헤더 불일치');
  const nameLen = buf.readUInt16LE(localOffset + 26);
  const extraLen = buf.readUInt16LE(localOffset + 28);
  const dataStart = localOffset + 30 + nameLen + extraLen;
  const data = buf.subarray(dataStart, dataStart + compressedSize);

  if (method === 0) return Buffer.from(data); // stored
  if (method === 8) return inflateRawSync(data); // deflate
  throw new Error(`ZIP: 지원하지 않는 압축 방식 (${method})`);
}
