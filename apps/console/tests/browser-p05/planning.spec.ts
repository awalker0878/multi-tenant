import { test, expect } from '@playwright/test';
import { readFileSync, writeFileSync } from 'node:fs';
import https from 'node:https';

test('compare exact destinations, retain uncertain command, review bound approval and hold revoked evidence', async ({ page, context }) => {
  const fixture=JSON.parse(readFileSync(process.env.P05_BROWSER_FIXTURE!, 'utf8'));
  const base=`/tenants/${fixture.tenant}/applications/${fixture.application}/environments/${fixture.environment}/planning`;
  const sites=`?sites=${fixture.sites.join(',')}`;
  await context.addCookies([fixture.author_cookie]);
  await page.goto(`${base}/assessments/${fixture.assessment}${sites}`);
  await expect(page.getByRole('heading',{name:'Requirement comparison'})).toBeVisible();
  await expect(page.getByRole('heading',{name:'openstack · eligible',exact:true})).toBeVisible();
  await expect(page.getByRole('heading',{name:'openstack · blocked',exact:true})).toBeVisible();
  await expect(page.getByText('observed capacity insufficient',{exact:false})).toBeVisible();
  await page.getByLabel('Intended executor IDs (comma separated)').fill(fixture.operator_id);
  writeFileSync(fixture.fault_file,JSON.stringify({path:fixture.planning_api_base+'/plans'}));
  await page.getByRole('button',{name:'Compile review proposal for this destination'}).first().click();
  await expect(page.getByRole('alert')).toContainText('result is uncertain');
  await expect(page.getByLabel('Intended executor IDs (comma separated)')).toBeDisabled();
  await page.getByRole('button',{name:'Retry the unchanged command'}).click();
  await expect(page.getByRole('heading',{name:'Immutable plan review',exact:true})).toBeVisible();
  await expect(page.getByRole('button',{name:'Request independent approval for this digest'})).toBeEnabled();
  await expect(page.getByText('Changes or removes state',{exact:true}).first()).toBeVisible();
  await page.setViewportSize({width:360,height:800});
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth+1)).toBeTruthy();
  await page.setViewportSize({width:1280,height:900});
  await page.getByRole('button',{name:'Request independent approval for this digest'}).focus();
  await expect(page.getByRole('button',{name:'Request independent approval for this digest'})).toBeFocused();
  await page.keyboard.press('Enter');
  await expect(page.getByRole('status').first()).toContainText('Approval requested');
  const qualified=JSON.parse(readFileSync(fixture.qualification_file,'utf8'));
  qualified.records[0].record.revoked=true;writeFileSync(fixture.qualification_file,JSON.stringify(qualified));
  await expect(page.getByRole('button',{name:'Request independent approval for this digest'})).toBeDisabled({timeout:35_000});
  await expect(page.getByText('exact tuple qualification missing or stale',{exact:true})).toBeVisible();
  const originalURL=page.url();
  const data=JSON.stringify({revision:fixture.membership.revision,subject:'p03-author',role:'author',state:'revoked',site_id:null,environment:null,expires_at:null});
  await new Promise<void>((resolve,reject)=>{
    const req=https.request(`${fixture.governance_url}/v1/tenants/${fixture.tenant}/memberships`,{method:'POST',ca:readFileSync(fixture.ca_file),headers:{Authorization:'Bearer '+fixture.console_workload,'X-Console-Session':fixture.admin_token,'Idempotency-Key':crypto.randomUUID(),'Content-Type':'application/json','Content-Length':Buffer.byteLength(data)}},res=>{res.resume();res.on('end',()=>res.statusCode===200?resolve():reject(new Error('revocation failed')));});req.on('error',reject);req.end(data);
  });
  await expect(page).toHaveURL(/\/account$/,{timeout:35_000});
  await page.goBack();
  await expect(page.getByRole('heading',{name:'Immutable plan review',exact:true})).toHaveCount(0);
  await page.goto(originalURL);
  await expect(page).toHaveURL(/\/account$/);
});

