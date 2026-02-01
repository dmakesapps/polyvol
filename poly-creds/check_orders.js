import { ClobClient } from "@polymarket/clob-client";
import { ethers } from "ethers";
import dotenv from "dotenv";
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
dotenv.config({ path: join(__dirname, "../config/.env") });

const PRIVATE_KEY = process.env.POLY_PRIVATE_KEY;
const API_KEY = process.env.POLY_API_KEY;
const API_SECRET = process.env.POLY_API_SECRET;
const PASSPHRASE = process.env.POLY_PASSPHRASE;
const FUNDER_ADDRESS = process.env.POLY_FUNDER_ADDRESS;

async function main() {
    const provider = new ethers.providers.JsonRpcProvider("https://polygon-rpc.com");
    const wallet = new ethers.Wallet(PRIVATE_KEY, provider);

    // Try Signature Type 2
    const client = new ClobClient(
        "https://clob.polymarket.com",
        137,
        wallet,
        { key: API_KEY, secret: API_SECRET, passphrase: PASSPHRASE },
        2, // NEW PROXY TYPE?
        FUNDER_ADDRESS
    );

    try {
        const orders = await client.getOpenOrders();
        console.log(`SigType 2 - Open Orders: ${orders.length}`);
    } catch (e) {
        console.log(`SigType 2 Failed: ${e.message}`);
    }
}

main().catch(console.error);
