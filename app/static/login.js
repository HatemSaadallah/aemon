'use strict';
// Sign in, then go to the Strategy Lab. The session cookie is HttpOnly, so this page never sees it.
const form = document.getElementById('login');
const error = document.getElementById('login-error');
const submit = document.getElementById('login-submit');

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  error.hidden = true;
  submit.disabled = true;
  try {
    const response = await fetch('/api/login', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'same-origin',
      body: JSON.stringify({ name: form.name.value.trim(), password: form.password.value }),
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'Sign-in failed');
    location.replace('/');
  } catch (failure) {
    error.textContent = failure.message;
    error.hidden = false;
    form.password.value = '';
    form.password.focus();
  } finally {
    submit.disabled = false;
  }
});
document.getElementById('name').focus();
