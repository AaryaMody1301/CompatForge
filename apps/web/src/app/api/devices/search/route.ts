import { NextRequest, NextResponse } from "next/server";

import { searchDevices } from "@/lib/catalog";

export function GET(request: NextRequest) {
  const query = request.nextUrl.searchParams.get("q")?.trim() ?? "";
  if (query.length < 2 || query.length > 80) {
    return NextResponse.json({ devices: [] });
  }
  const devices = searchDevices(query).slice(0, 8).map((device) => ({
    id: device.id,
    name: `${device.manufacturer} ${device.name}`,
  }));
  return NextResponse.json({ devices }, { headers: { "Cache-Control": "no-store" } });
}
