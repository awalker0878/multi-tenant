import { test, expect } from '@playwright/test';
import { readFileSync } from 'node:fs';
test('completed evidence has exact custody, simulation label and independent review',async({page,context})=>{
 const f=JSON.parse(readFileSync(process.env.P06_BROWSER_FIXTURE!,'utf8')),job=f.p06_completed,s=job.scope;
 await context.addCookies([f.reviewer_cookie]);
 await page.goto(`/tenants/${f.tenant}/sites/${s.site_id}/applications/${s.resource_id}/environments/${s.environment}/jobs/${job.id}`);
 await expect(page.getByRole('heading',{name:'completed',exact:true})).toBeVisible();
 await expect(page.getByRole('button',{name:'Emergency stop',exact:true})).toBeDisabled();
 await page.getByRole('link',{name:'Inspect verified evidence'}).click();
 await expect(page.getByRole('heading',{name:'Simulation evidence',exact:true})).toBeVisible();
 await expect(page.getByText(job.evidence.digest,{exact:true})).toBeVisible();
 await expect(page.getByText('accepted simulation',{exact:false})).toBeVisible();
 await expect(page.getByText('E2 isolated simulation evidence.',{exact:false})).toBeVisible();
 await page.setViewportSize({width:360,height:800});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth+1)).toBeTruthy();
 await page.getByRole('link',{name:'Back to job'}).focus();await page.keyboard.press('Enter');
 await expect(page.getByRole('heading',{name:'Simulation job',exact:true})).toBeVisible();
});
