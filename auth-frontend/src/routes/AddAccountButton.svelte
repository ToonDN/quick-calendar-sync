<script lang="ts">
	import { PUBLIC_GOOGLE_CLIENT_ID } from '$env/static/public';

	const clientIdParam = `client_id=${PUBLIC_GOOGLE_CLIENT_ID}`;
	const redirectUriParam = `redirect_uri=http://localhost:5173/`;
	const responseTypeParam = 'response_type=code';
	const scopeParam = 'scope=email https://www.googleapis.com/auth/calendar';
	const accessTypeParam = 'access_type=offline';
	const promptParam = 'prompt=consent';
	const params = `?${responseTypeParam}&${clientIdParam}&${scopeParam}&${redirectUriParam}&${accessTypeParam}&${promptParam}`;

	const url = `https://accounts.google.com/o/oauth2/v2/auth${params}`;
</script>

<div class="h-10 flex items-center justify-between mt-4">
	<a href={url} class="w-full h-full bg-slate-600 rounded-md">
		<div class="h-full flex flex-col ml-3 ">
			<span class="pt-2 text-white"> Add account </span>
		</div>
	</a>
</div>