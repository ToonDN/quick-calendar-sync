<script>
	import AddAccountButton from "./AddAccountButton.svelte";
	import fs from "fs";

	const getAccounts = () => {
		const files = fs.readdirSync("../tokens/")
		return files
	}

</script>

{#each getAccounts() as account}
	<div class="h-10 flex items-center justify-between mt-4">
		<div class="w-full h-full bg-slate-600 rounded-md">
			<div class="h-full flex flex-col ml-3 ">
				<span class="pt-2 text-white"> {account} </span>
			</div>
		</div>
	</div>
{/each}

<AddAccountButton/>