import { test, expect } from '@playwright/test';
import { readFileSync, writeFileSync, unlinkSync } from 'node:fs';
import https from 'node:https';

test('held unknown effects, stale authority, lost control receipt, cancellation and revoked history', async ({page,context,browser})=>{
  const f=JSON.parse(readFileSync(process.env.P06_BROWSER_FIXTURE!,'utf8'));
  const job=f.p06_jobs[1],scope=f.p06_plans[1].content.scope;
  const base=`/tenants/${f.tenant}/sites/${scope.site_id}/applications/${scope.resource_id}/environments/${scope.environment}/jobs/${job.id}`;
  await context.addCookies([f.operator_cookie]);await page.goto(base);
  await expect(page.getByRole('heading',{name:'Simulation job',exact:true})).toBeVisible();
  await expect(page.getByText('An effect may have been accepted.',{exact:false})).toBeVisible();
  await expect(page.getByText('The target write boundary has been reached',{exact:false})).toBeVisible();
  await expect(page.getByRole('button',{name:'Resume after review'})).toBeDisabled();
  await page.setViewportSize({width:360,height:800});
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth+1)).toBeTruthy();
  await page.setViewportSize({width:1280,height:900});
  writeFileSync(f.p06_fault_file,JSON.stringify({mode:'unavailable'}));
  await expect(page.getByRole('button',{name:'Emergency stop',exact:true})).toBeDisabled({timeout:20000});
  await expect(page.getByRole('alert').first()).toContainText('Current job state is unavailable');
  unlinkSync(f.p06_fault_file);await page.evaluate(()=>window.dispatchEvent(new Event('online')));
  await expect(page.getByRole('button',{name:'Emergency stop',exact:true})).toBeEnabled();
  writeFileSync(f.p06_fault_file,JSON.stringify({path:`/v1/tenants/${f.tenant}/jobs/${job.id}/commands`}));
  await page.getByRole('button',{name:'Emergency stop',exact:true}).focus();await page.keyboard.press('Enter');
  await expect(page.getByRole('button',{name:'Recover command receipt'})).toBeVisible();
  await expect(page.getByRole('button',{name:'Request cancellation'})).toBeDisabled();
  await page.getByRole('button',{name:'Recover command receipt'}).click();
  await expect(page.getByRole('status').filter({hasText:'stop request accepted'})).toBeVisible();
  await page.getByRole('button',{name:'Request cancellation'}).click();
  await expect(page.getByText('Cancellation was requested.',{exact:false})).toBeVisible();
  // An independent reader sees the job, but loses access as soon as its membership is revoked.
  const reviewer=await browser.newContext();await reviewer.addCookies([f.reader_cookie]);const review=await reviewer.newPage();await review.goto('http://127.0.0.1:8031'+base);
  await expect(review.getByRole('heading',{name:'Simulation job',exact:true})).toBeVisible();
  const data=JSON.stringify({revision:f.reader_member.revision,subject:'p03-outsider',role:'reader',state:'revoked',site_id:null,environment:null,expires_at:null});
  await new Promise<void>((resolve,reject)=>{const req=https.request(`${f.governance_url}/v1/tenants/${f.tenant}/memberships`,{method:'POST',ca:readFileSync(f.ca_file),headers:{Authorization:'Bearer '+f.console_workload,'X-Console-Session':f.admin_token,'Idempotency-Key':crypto.randomUUID(),'Content-Type':'application/json','Content-Length':Buffer.byteLength(data)}},res=>{res.resume();res.on('end',()=>res.statusCode===200?resolve():reject(new Error('reviewer revocation failed')));});req.on('error',reject);req.end(data);});
  await expect(review).toHaveURL(/\/account$/,{timeout:35000});await review.goBack();await expect(review.getByRole('heading',{name:'Simulation job',exact:true})).toHaveCount(0);await reviewer.close();
});
