#!/usr/bin/env python3
# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║  Script : force_delete_sal_and_rg.py                                      ║
# ║  Purpose: פתרון מוּכּח למחיקת Resource Group שנתקע בגלל SAL יתום          ║
# ║           (Service-Association-Link) שיצרה סביבת Azure Container Apps.   ║
# ║           1. מחיקת ה-SAL ב-API היציב ‎2018-10-01                         ║
# ║           2. הסרת האצילה (delegation) מה-Subnet                          ║
# ║           3. מחיקת ה-Subnet                                              ║
# ║           4. (רשות) מחיקת ה-VNet                                         ║
# ║           5. מחיקת ה-Resource Group                                      ║
# ║  Author : Roi (2025-07-08)                                               ║
# ║  Location: tests/debug/ (following new script organization policy)       ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

import subprocess
import json
import time
import sys
from datetime import datetime
from typing import List, Tuple

# ------------------  כלי עזר להרצת ‎az cli -----------------
def run_az(cmd: List[str], desc: str, timeout: int = 120) -> Tuple[bool, str, str]:
    print(f"\n🔧 {desc}\nCMD: {' '.join(cmd)}")
    print("-" * 60)
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        ok, out, err = res.returncode == 0, res.stdout.strip(), res.stderr.strip()
        print(f"RC={res.returncode}\n{out if out else ''}{err if err else ''}")
        return ok, out, err
    except Exception as exc:
        print(f"💥 EXCEPTION: {exc}")
        return False, "", str(exc)

# ------------------  פרטי Subscription -----------------
def get_subscription_id() -> str:
    ok, out, _ = run_az(["az", "account", "show", "-o", "json"], "בדיקת התחברות")
    if not ok:
        sys.exit("❌ לא מחובר ל-Azure (az login)")
    return json.loads(out)["id"]

# ------------------  מציאת SAL-ים יתומים -----------------
def list_sal_ids(rg: str) -> List[str]:
    ok, out, _ = run_az(
        [
            "az", "network", "vnet", "subnet", "show",
            "-g", rg, "--vnet-name", "agent-vnet-test", "-n", "agent-subnet",
            "-o", "json"
        ],
        "שליפת serviceAssociationLinks"
    )
    if not ok:
        return []
    props = json.loads(out)
    return [link["id"] for link in props.get("serviceAssociationLinks", [])]

# ------------------  מחיקת SAL יחיד -----------------
def delete_sal(sal_id: str) -> bool:
    return run_az(
        ["az", "resource", "delete", "--ids", sal_id, "--api-version", "2018-10-01"],
        f"מחיקת SAL {sal_id.split('/')[-1]}"
    )[0]

# ------------------  הסרת Delegation -----------------
def remove_delegation(rg: str) -> bool:
    return run_az(
        [
            "az", "network", "vnet", "subnet", "update",
            "-g", rg, "--vnet-name", "agent-vnet-test", "-n", "agent-subnet",
            "--remove", "delegations"
        ],
        "הסרת Delegation מה-Subnet"
    )[0]

# ------------------  מחיקת Subnet -----------------
def delete_subnet(rg: str) -> bool:
    return run_az(
        [
            "az", "network", "vnet", "subnet", "delete",
            "-g", rg, "--vnet-name", "agent-vnet-test", "-n", "agent-subnet"
        ],
        "מחיקת Subnet"
    )[0]

# ------------------  מחיקת VNet (רשות) -----------------
def delete_vnet(rg: str) -> None:
    run_az(
        ["az", "network", "vnet", "delete", "-g", rg, "-n", "agent-vnet-test"],
        "מחיקת VNet (רשות)"
    )

# ------------------  מחיקת Resource Group -----------------
def delete_rg(rg: str) -> bool:
    return run_az(["az", "group", "delete", "-n", rg, "--yes"], "מחיקת Resource Group")[0]

# ------------------  אימות מחיקה -----------------
def verify_rg_gone(rg: str) -> bool:
    ok, *_ = run_az(["az", "group", "show", "-n", rg], "וידוא קיום RG")
    return not ok  # אם הפקודה נכשלה – ה-RG איננו

# ------------------  MAIN -----------------
def main() -> int:
    rg = "bciep-test-8"
    print(f"\n🚀 START  {datetime.now():%F %T}\nTarget RG: {rg}\n" + "═" * 60)
    print("📍 Script Location: tests/debug/ (following new organization policy)")
    print("🎯 Using proven Hebrew-commented approach with az resource delete")
    print("=" * 80)

    if input("Type DELETE SAL NOW to continue: ").strip() != "DELETE SAL NOW":
        print("❌ בוטל ע״י המשתמש")
        return 1

    sub = get_subscription_id()

    # 1. SAL s
    sal_ids = list_sal_ids(rg)
    if not sal_ids:
        print("ℹ️ לא נמצאו SAL-ים – ממשיך...")
    else:
        for sid in sal_ids:
            if delete_sal(sid):
                print("✅ SAL נמחק")
            else:
                print("⚠️ מחיקת SAL נכשלה (ממשיך)")

        time.sleep(10)  # תן זמן לסנכרון

    # 2. Delegation
    if not remove_delegation(rg):
        print("❌ לא ניתן להסיר Delegation – הפסקה")
        return 1

    # 3-4. Subnet & VNet
    if not delete_subnet(rg):
        print("❌ מחיקת Subnet נכשלה")
        return 1
    delete_vnet(rg)  # רשות

    # 5. RG
    if not delete_rg(rg):
        print("❌ מחיקת ה-RG נכשלה")
        return 1

    # Verify
    print("⏳ ממתין לאימות (30 ש׳)…")
    time.sleep(30)
    if verify_rg_gone(rg):
        print("🎉 ה-RG נמחק בהצלחה!")
        return 0

    print("⚠️ ה-RG עדיין קיים (ייתכן בתהליך מחיקה)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
