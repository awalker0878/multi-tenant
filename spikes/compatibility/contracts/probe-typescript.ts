import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { Configuration, SamplesApi, SampleFromJSON, SampleToJSON, type Sample } from './typescript-fetch/src/index';

async function main(): Promise<void> {
    const fixtures = JSON.parse(readFileSync(process.argv[2]!, 'utf8'));
    const wire = fixtures.find((x: { id: string }) => x.id === 'sample-valid').value;
    const model: Sample = SampleFromJSON(wire);
    assert.equal(model.revision, '9007199254740993');
    assert.equal(model.note, null);
    const back = SampleToJSON(model);
    for (const key of Object.keys(wire)) assert.deepEqual(back[key], wire[key]);
    const extended = SampleFromJSON({ ...wire, future_display: 'synthetic' });
    assert.equal(extended['future_display'], 'synthetic');
    // Decoding is not runtime validation: guard the wire data before this adapter.
    const invalid = SampleFromJSON({ ...wire, phase: 'executing' });
    assert.equal(invalid.phase, 'executing');
    let calls = 0;
    const client = new SamplesApi(new Configuration({
        basePath: 'https://contract.invalid', accessToken: 'synthetic-local-fixture',
        fetchApi: async (input, init) => {
            calls++;
            assert.equal(String(input), 'https://contract.invalid/samples/sample_a1');
            assert.equal(new Headers(init?.headers).get('authorization'), 'Bearer synthetic-local-fixture');
            return new Response(JSON.stringify(wire), { status: 200, headers: { 'Content-Type': 'application/json' } });
        },
    }));
    const reply = await client.getSample({ sampleId: 'sample_a1' });
    assert.equal(reply.revision, wire.revision);
    assert.equal(calls, 1);
    console.log(JSON.stringify({ status: 'PASS', mock_transport_calls: calls,
        known_gap: 'generated decoder accepts an unknown enum; boundary schema validation is mandatory' }));
}
void main();
