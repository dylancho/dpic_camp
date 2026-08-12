import { CompanyInputSchema } from '@/lib/contract';
import { runPipeline } from '@/lib/agents/orchestrator';

/** 4개 에이전트 병렬 + 보고서 스트리밍이라 넉넉히 잡는다 */
export const maxDuration = 300;

export async function POST(req: Request) {
  const parsed = CompanyInputSchema.safeParse(await req.json());
  if (!parsed.success) {
    return Response.json({ error: '기업명을 입력해 주세요.' }, { status: 400 });
  }

  const encoder = new TextEncoder();
  const stream = new ReadableStream({
    async start(controller) {
      try {
        for await (const ev of runPipeline(parsed.data)) {
          controller.enqueue(encoder.encode(JSON.stringify(ev) + '\n'));
        }
      } catch (e) {
        controller.enqueue(
          encoder.encode(JSON.stringify({ type: 'error', message: (e as Error).message }) + '\n'),
        );
      } finally {
        controller.close();
      }
    },
  });

  return new Response(stream, {
    headers: {
      'Content-Type': 'application/x-ndjson; charset=utf-8',
      'Cache-Control': 'no-cache, no-transform',
      'X-Accel-Buffering': 'no',
    },
  });
}
