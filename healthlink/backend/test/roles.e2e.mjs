import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { createHash } from 'node:crypto';

const base = process.env.HEALTHLINK_TEST_URL || 'http://localhost:3000/api';
const password = 'healthlink-demo-2026';
async function request(path, options = {}, cookie = '') {
  const response = await fetch(base + path, { ...options, headers: { 'Content-Type': 'application/json', ...(cookie ? { Cookie: cookie } : {}), ...options.headers } });
  const body = await response.json().catch(() => null);
  return { status: response.status, body, cookie: response.headers.get('set-cookie')?.split(';')[0], headers: response.headers };
}
async function login(email, role) {
  const result = await request('/auth/login', { method: 'POST', body: JSON.stringify({ email, password, role }) });
  assert.equal(result.status, 200);
  assert.ok(result.cookie);
  assert.match(result.headers.get('set-cookie'), /HttpOnly/i);
  assert.match(result.headers.get('set-cookie'), /SameSite=Lax/i);
  return result;
}

test('private routes reject anonymous access', async () => {
  for (const path of ['/doctors', '/consultations', '/doctor/dashboard', '/admin/dashboard']) {
    assert.equal((await request(path)).status, 401, path);
  }
});
test('invalid credentials and forged login role cannot create a session', async () => {
  const bad = await request('/auth/login', { method: 'POST', body: JSON.stringify({ email: 'john@healthlink.local', password: 'wrong-password', role: 'PATIENT' }) });
  assert.equal(bad.status, 401);
  assert.equal(bad.cookie, undefined);
  const forged = await request('/auth/login', { method: 'POST', body: JSON.stringify({ email: 'john@healthlink.local', password, role: 'ADMIN' }) });
  assert.equal(forged.status, 401);
});
test('patient identity survives requests and logout revokes the session', async () => {
  const patient = await login('john@healthlink.local', 'PATIENT');
  const me = await request('/auth/me', {}, patient.cookie);
  assert.equal(me.body.role, 'PATIENT');
  assert.equal(me.body.email, 'john@healthlink.local');
  assert.equal(me.body.name, 'John');
  assert.equal(me.body.passwordHash, undefined);
  assert.equal((await request('/doctor/dashboard', {}, patient.cookie)).status, 403);
  assert.equal((await request('/admin/dashboard', {}, patient.cookie)).status, 403);
  assert.equal((await request('/auth/logout', { method: 'POST', body: '{}' }, patient.cookie)).status, 200);
  assert.equal((await request('/auth/me', {}, patient.cookie)).status, 401);
});
test('doctor access is role restricted and scoped to their own appointments', async () => {
  const doctor = await login('sarah.lim@healthlink.local', 'DOCTOR');
  const dashboard = await request('/doctor/dashboard', {}, doctor.cookie);
  assert.equal(dashboard.status, 200);
  assert.equal(dashboard.body.doctor.name, 'Dr. Sarah Lim');
  assert.ok(dashboard.body.consultations.every(c => c.doctorId === dashboard.body.doctor.id));
  assert.equal((await request('/admin/dashboard', {}, doctor.cookie)).status, 403);
  assert.equal((await request('/consultations', { method: 'POST', body: JSON.stringify({}) }, doctor.cookie)).status, 403);
});
test('booking is patient scoped and only its doctor can update status', async () => {
  const patient = await login('john@healthlink.local', 'PATIENT');
  const doctors = await request('/doctors', {}, patient.cookie);
  const sarah = doctors.body.find(d => d.name === 'Dr. Sarah Lim');
  const slot = sarah.availability[0];
  assert.ok(slot, 'Sarah must have a free seeded slot');
  const payload = { doctorId: sarah.id, type: 'CHAT', preferredTime: slot.startTime, reasonForVisit: 'Role acceptance test booking.' };
  const created = await request('/consultations', { method: 'POST', body: JSON.stringify(payload) }, patient.cookie);
  assert.equal(created.status, 201);
  const id = created.body.id;
  assert.equal((await request('/consultations', { method: 'POST', body: JSON.stringify(payload) }, patient.cookie)).status, 409);
  assert.equal((await request('/consultations', { method: 'POST', body: '{}' }, patient.cookie)).status, 400);
  assert.equal((await request('/consultations', { method: 'POST', body: JSON.stringify({ ...payload, reasonForVisit: '     ' }) }, patient.cookie)).status, 400);
  const saved = (await request('/consultations', {}, patient.cookie)).body.find(c => c.id === id);
  assert.equal(saved.reasonForVisit, payload.reasonForVisit);
  const otherPatient = await login('ahmad@healthlink.local', 'PATIENT');
  assert.equal(otherPatient.body.name, 'Ahmad');
  assert.ok(!(await request('/consultations', {}, otherPatient.cookie)).body.some(c => c.id === id));
  const wrongDoctor = await login('aiman.rashid@healthlink.local', 'DOCTOR');
  assert.equal((await request('/doctor/consultations/' + id + '/status', { method: 'PATCH', body: JSON.stringify({ status: 'COMPLETED' }) }, wrongDoctor.cookie)).status, 404);
  assert.equal((await request('/doctor/consultations/' + id + '/status', { method: 'PATCH', body: JSON.stringify({ status: 'COMPLETED' }) }, patient.cookie)).status, 403);
  const sarahSession = await login('sarah.lim@healthlink.local', 'DOCTOR');
  assert.equal((await request('/doctor/consultations/' + id + '/status', { method: 'PATCH', body: JSON.stringify({ status: 'COMPLETED' }) }, sarahSession.cookie)).status, 200);
  assert.equal((await request('/consultations', {}, patient.cookie)).body.find(c => c.id === id).status, 'COMPLETED');
});
test('doctor can add and remove a free slot but cannot remove a booked slot', async () => {
  const doctor = await login('sarah.lim@healthlink.local', 'DOCTOR');
  const start = new Date(Date.now() + 21 * 86400000);
  const created = await request('/doctor/availability', { method: 'POST', body: JSON.stringify({ startTime: start.toISOString(), endTime: new Date(start.getTime() + 1800000).toISOString() }) }, doctor.cookie);
  assert.equal(created.status, 201);
  assert.equal((await request('/doctor/availability/' + created.body.id, { method: 'DELETE' }, doctor.cookie)).status, 200);
  const dash = await request('/doctor/dashboard', {}, doctor.cookie);
  const booked = dash.body.availability.find(s => s.isBooked);
  assert.ok(booked);
  assert.equal((await request('/doctor/availability/' + booked.id, { method: 'DELETE' }, doctor.cookie)).status, 409);
  assert.equal((await request('/doctor/availability', { method: 'POST', body: JSON.stringify({ startTime: start.toISOString(), endTime: new Date(start.getTime() - 60000).toISOString() }) }, doctor.cookie)).status, 400);
});
test('admin sees overview and visibility changes affect patient doctor listing', async () => {
  const admin = await login('admin@healthlink.local', 'ADMIN');
  const patient = await login('john@healthlink.local', 'PATIENT');
  const dashboard = await request('/admin/dashboard', {}, admin.cookie);
  assert.equal(dashboard.status, 200);
  assert.ok(dashboard.body.patients.length >= 2);
  const doctor = dashboard.body.doctors.find(d => d.name === 'Dr. Priya Nair');
  try {
    assert.equal((await request('/admin/doctors/' + doctor.id, { method: 'PATCH', body: JSON.stringify({ active: false }) }, admin.cookie)).status, 200);
    assert.ok(!(await request('/doctors', {}, patient.cookie)).body.some(d => d.id === doctor.id));
    assert.equal((await request('/admin/doctors/' + doctor.id, { method: 'PATCH', body: JSON.stringify({ active: true }) }, patient.cookie)).status, 403);
  } finally {
    await request('/admin/doctors/' + doctor.id, { method: 'PATCH', body: JSON.stringify({ active: true }) }, admin.cookie);
  }
});
test('cross-site writes are rejected without changing the session', async () => {
  const patient = await login('john@healthlink.local', 'PATIENT');
  assert.equal((await request('/auth/logout', { method: 'POST', headers: { Origin: 'https://untrusted.example' }, body: '{}' }, patient.cookie)).status, 403);
  assert.equal((await request('/auth/me', {}, patient.cookie)).status, 200);
});

test('expired and tampered session tokens cannot access patient data', async () => {
  const require = createRequire(import.meta.url);
  const { PrismaClient } = require('@prisma/client');
  const prisma = new PrismaClient();
  const patient = await login('john@healthlink.local', 'PATIENT');
  const token = patient.cookie.split('=')[1];
  try {
    await prisma.authSession.update({ where: { tokenHash: createHash('sha256').update(token).digest('hex') }, data: { expiresAt: new Date(Date.now() - 1000) } });
    assert.equal((await request('/consultations', {}, patient.cookie)).status, 401);
    assert.equal((await request('/consultations', {}, 'healthlink_session=' + '0'.repeat(64))).status, 401);
  } finally {
    await prisma.authSession.deleteMany({ where: { tokenHash: createHash('sha256').update(token).digest('hex') } });
    await prisma.$disconnect();
  }
});
