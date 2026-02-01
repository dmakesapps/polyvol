import { ClobClient } from "@polymarket/clob-client";
import { ethers } from "ethers";
import dotenv from "dotenv";
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

// Load .env from parent directory
const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
dotenv.config({ path: join(__dirname, "../config/.env") });

const PRIVATE_KEY = process.env.POLY_PRIVATE_KEY;
const API_KEY = process.env.POLY_API_KEY;
const API_SECRET = process.env.POLY_API_SECRET;
const PASSPHRASE = process.env.POLY_PASSPHRASE;
const FUNDER_ADDRESS = process.env.POLY_FUNDER_ADDRESS;

if (!PRIVATE_KEY || !API_KEY || !FUNDER_ADDRESS) {
    console.error(JSON.stringify({ success: false, error: "Missing credentials in .env" }));
    process.exit(1);
}

const HOST = "https://clob.polymarket.com";
const CHAIN_ID = 137; // Polygon Mainnet
const RPC_URL = "https://polygon-rpc.com";

async function main() {
    // Parse args: node trade.js <tokenId> <side> <price> <size>
    const args = process.argv.slice(2);
    if (args.length < 4) {
        console.error(JSON.stringify({ success: false, error: "Usage: node trade.js <tokenId> <side> <price> <size>" }));
        process.exit(1);
    }

    const tokenId = args[0];
    const side = args[1].toUpperCase(); // BUY or SELL
    const price = parseFloat(args[2]);
    const size = parseFloat(args[3]);

    try {
        // Setup Provider & Signer
        const provider = new ethers.providers.JsonRpcProvider(RPC_URL);
        const wallet = new ethers.Wallet(PRIVATE_KEY, provider);

        // Initialize Official Client
        // Note: ethers v5 is required by clob-client usually.
        // Constructor signature: (host, chainId, signer, creds, signatureType, funderAddress, ...)
        // We need to pass 1 (Proxy) for signatureType, then funderAddress.
        const client = new ClobClient(
            HOST,
            CHAIN_ID,
            wallet,
            {
                key: API_KEY,
                secret: API_SECRET,
                passphrase: PASSPHRASE
            },
            1, // signatureType: 1 (Proxy)
            FUNDER_ADDRESS // 6th arg
        );

        // Helper to place order
        const placeOrder = async (feeRate) => {
            const order = await client.createOrder({
                tokenID: tokenId,
                price: price,
                side: side === "BUY" ? "BUY" : "SELL",
                size: size,
                feeRateBps: feeRate,
                nonce: 0
            });
            return await client.postOrder(order);
        };

        try {
            const resp = await placeOrder(0);
            if (resp && resp.orderID) {
                console.log(JSON.stringify({ success: true, orderId: resp.orderID, price: price, size: size }));
            } else {
                console.log(JSON.stringify({ success: true, resp: resp }));
            }
        } catch (err) {
            // Check for fee rate error
            const msg = err.message || "";
            const match = msg.match(/fee rate for the market must be (\d+)/);
            if (match) {
                const requiredFee = parseInt(match[1]);
                // console.log(`Retrying with fee rate: ${requiredFee}`);
                const resp = await placeOrder(requiredFee);
                if (resp && resp.orderID) {
                    console.log(JSON.stringify({ success: true, orderId: resp.orderID, price: price, size: size, retried: true }));
                } else {
                    console.log(JSON.stringify({ success: true, resp: resp }));
                }
            } else {
                throw err;
            }
        }

    } catch (error) {
        console.log(JSON.stringify({ success: false, error: error.message }));
        process.exit(1);
    }
}

main().catch(e => {
    console.log(JSON.stringify({ success: false, error: e.message }));
    process.exit(1);
});
