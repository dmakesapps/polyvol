import { ethers } from "ethers";
import dotenv from "dotenv";
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
dotenv.config({ path: join(__dirname, "../config/.env") });

const PRIVATE_KEY = process.env.POLY_PRIVATE_KEY;
const FUNDER_ADDRESS = process.env.POLY_FUNDER_ADDRESS;
const RPC_URL = "https://polygon-rpc.com";

const USDC_ADDR = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174";
const EXCHANGE_ADDR = "0xC5d563A36AE78145C45a50134d48A1215220f80a"; // Current
const LEGACY_EXCHANGE = "0x4bFb41d5B3570DeFd03C39a9A4D8dE6Bd8B8982E"; // Legacy

const abi = [
    "function balanceOf(address account) view returns (uint256)",
    "function allowance(address owner, address spender) view returns (uint256)",
    "function decimals() view returns (uint8)"
];

async function main() {
    const provider = new ethers.providers.JsonRpcProvider(RPC_URL);
    const wallet = new ethers.Wallet(PRIVATE_KEY, provider);
    const usdc = new ethers.Contract(USDC_ADDR, abi, provider);

    console.log(`Checking Funder: ${FUNDER_ADDRESS}`);

    const decimals = 6;
    const balance = await usdc.balanceOf(FUNDER_ADDRESS);
    const allowanceCurrent = await usdc.allowance(FUNDER_ADDRESS, EXCHANGE_ADDR);
    const allowanceLegacy = await usdc.allowance(FUNDER_ADDRESS, LEGACY_EXCHANGE);

    console.log(`Funder USDC Balance: ${ethers.utils.formatUnits(balance, decimals)}`);
    console.log(`Allowance for Current Exchange: ${ethers.utils.formatUnits(allowanceCurrent, decimals)}`);
    console.log(`Allowance for Legacy Exchange: ${ethers.utils.formatUnits(allowanceLegacy, decimals)}`);
}

main().catch(console.error);
