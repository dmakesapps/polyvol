import { ClobClient } from "@polymarket/clob-client";
import { ethers } from "ethers";

const PRIVATE_KEY = "0x2a0dbe856c9c85b00659ae47a0e4eaf201f819b1304de60cf33c307ddf03cde0";
const HOST = "https://clob.polymarket.com";
const CHAIN_ID = 137;

const RPC_URL = "https://polygon-rpc.com";

async function main() {
    console.log("============================================================");
    console.log("Polymarket API Credential Derivation");
    console.log("============================================================\n");

    const provider = new ethers.providers.JsonRpcProvider(RPC_URL);
    const wallet = new ethers.Wallet(PRIVATE_KEY, provider);

    console.log(`Wallet Address: ${wallet.address}`);
    console.log();

    const client = new ClobClient(HOST, CHAIN_ID, wallet);

    // First try to get existing API keys
    console.log("1. Checking for existing API keys...\n");
    try {
        const keys = await client.getApiKeys();
        console.log("Existing API keys:", JSON.stringify(keys, null, 2));
    } catch (e) {
        console.log("No existing keys or error:", e.message);
    }

    // Try createOrDeriveApiCreds which should handle both cases
    console.log("\n2. Using createOrDeriveApiCreds...\n");
    try {
        const creds = await client.createOrDeriveApiCreds();
        console.log("============================================================");
        console.log("SUCCESS! Your API credentials:");
        console.log("============================================================");
        console.log();
        console.log(`POLY_API_KEY=${creds.apiKey}`);
        console.log(`POLY_API_SECRET=${creds.secret}`);
        console.log(`POLY_PASSPHRASE=${creds.passphrase}`);
    } catch (e) {
        console.log(`Error: ${e.message}`);

        // Last resort: derive and create separately  
        console.log("\n3. Trying to derive first, then create...\n");
        try {
            // Derive gets deterministic secret/passphrase
            const derived = await client.deriveApiKey();
            console.log("Derived credentials:", JSON.stringify(derived, null, 2));

            // Now try to create with those
            const created = await client.createApiKey();
            console.log("Created key:", JSON.stringify(created, null, 2));
        } catch (e2) {
            console.log("Final error:", e2.message);
        }
    }
}

main().catch(console.error);
