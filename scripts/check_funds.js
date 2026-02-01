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
const EXCHANGE_ADDR = "0x4bFbB674825902966Bc008779603f0Ad6Cc4A576"; // Polymarket CTF Exchange on Polygon

const abi = [
    "function balance_of(address account) view returns (uint256)",
    "function allowance(address owner, address spender) view returns (uint256)",
    "function approve(address spender, uint256 amount) returns (bool)",
    "function decimals() view returns (uint8)"
];

async function main() {
    const provider = new ethers.providers.JsonRpcProvider(RPC_URL);
    const wallet = new ethers.Wallet(PRIVATE_KEY, provider);
    const usdc = new ethers.Contract(USDC_ADDR, abi, provider);
    const usdcWithSigner = usdc.connect(wallet);

    console.log(`Checking Funder: ${FUNDER_ADDRESS}`);
    console.log(`Checking Signer: ${wallet.address}`);

    const decimals = 6;
    const balance = await usdcWithSigner.balance_of(FUNDER_ADDRESS);
    const allowance = await usdcWithSigner.allowance(FUNDER_ADDRESS, EXCHANGE_ADDR);

    console.log(`USDC Balance: ${ethers.utils.formatUnits(balance, decimals)}`);
    console.log(`USDC Allowance for Exchange: ${ethers.utils.formatUnits(allowance, decimals)}`);

    if (balance.gt(0) && allowance.lt(balance)) {
        console.log("Allowance is too low. Attempting to approve...");
        // This only works if FUNDER_ADDRESS == Signer or if we have a way to make the Proxy approve.
        // If FUNDER_ADDRESS is a Proxy, the approve call needs to go through the Proxy.
        if (FUNDER_ADDRESS.toLowerCase() === wallet.address.toLowerCase()) {
            const tx = await usdcWithSigner.approve(EXCHANGE_ADDR, ethers.constants.MaxUint256);
            console.log(`Approval TX: ${tx.hash}`);
            await tx.wait();
            console.log("Approved successfully.");
        } else {
            console.log("Funder address is different from Signer. You likely need to approve via Polymarket UI or Proxy management.");
        }
    }
}

main().catch(console.error);
