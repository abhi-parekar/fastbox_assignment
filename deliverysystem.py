import json
import math
import csv
import sys
import os
import glob


def euclidean_distance(point_a, point_b):
    return math.sqrt((point_a[0] - point_b[0]) ** 2 + (point_a[1] - point_b[1]) ** 2)


def load_data(filepath):
    with open(filepath, "r") as f:
        data = json.load(f)

    raw_wh = data["warehouses"]
    if isinstance(raw_wh, dict):
        warehouses = {wid: loc for wid, loc in raw_wh.items()}
    else:
        warehouses = {w["id"]: w["location"] for w in raw_wh}

    raw_ag = data["agents"]
    if isinstance(raw_ag, dict):
        agents = {aid: loc for aid, loc in raw_ag.items()}
    else:
        agents = {a["id"]: a["location"] for a in raw_ag}

    packages = []
    for pkg in data["packages"]:
        packages.append({
            "id": pkg["id"],
            "warehouse": pkg.get("warehouse") or pkg.get("warehouse_id"),
            "destination": pkg["destination"]
        })

    return warehouses, agents, packages


def assign_packages(warehouses, agents, packages):
    assignments = {aid: [] for aid in agents}

    for pkg in packages:
        warehouse_loc = warehouses[pkg["warehouse"]]
        nearest_agent = None
        min_dist = float("inf")

        for aid, agent_loc in agents.items():
            dist = euclidean_distance(agent_loc, warehouse_loc)
            if dist < min_dist:
                min_dist = dist
                nearest_agent = aid

        assignments[nearest_agent].append(pkg)

    return assignments


def simulate_delivery(warehouses, agents, assignments):
    results = {}

    for aid, pkgs in assignments.items():
        current_pos = list(agents[aid])
        total_dist = 0.0

        for pkg in pkgs:
            warehouse_loc = warehouses[pkg["warehouse"]]
            destination = pkg["destination"]

            total_dist += euclidean_distance(current_pos, warehouse_loc)
            current_pos = warehouse_loc

            total_dist += euclidean_distance(current_pos, destination)
            current_pos = destination

        results[aid] = {
            "packages_delivered": len(pkgs),
            "total_distance": round(total_dist, 2)
        }

    return results


def generate_report(simulation_results):
    report = {}
    best_agent = None
    best_eff = float("inf")

    for aid, res in simulation_results.items():
        pkgs = res["packages_delivered"]
        dist = res["total_distance"]
        efficiency = round(dist / pkgs, 2) if pkgs > 0 else 0.0

        report[aid] = {
            "packages_delivered": pkgs,
            "total_distance": dist,
            "efficiency": efficiency
        }

        if pkgs > 0 and efficiency < best_eff:
            best_eff = efficiency
            best_agent = aid

    report["best_agent"] = best_agent
    return report


def save_report(report, output_path="report.json"):
    folder = os.path.dirname(output_path)
    if folder:
        os.makedirs(folder, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(report, f, indent=4)
    print(f"Report saved to '{output_path}'")


def visualise_routes(warehouses, agents, assignments, grid_size=20):
    print("\n── ASCII Route Map ──")
    grid = [["." for _ in range(grid_size + 1)] for _ in range(grid_size + 1)]

    def scale(coord, axis_max=110):
        return min(grid_size, int(coord * grid_size / axis_max))

    for wid, loc in warehouses.items():
        r, c = grid_size - scale(loc[1]), scale(loc[0])
        grid[r][c] = "W"

    for aid, pkgs in assignments.items():
        aloc = agents[aid]
        r, c = grid_size - scale(aloc[1]), scale(aloc[0])
        grid[r][c] = "A"
        for pkg in pkgs:
            dest = pkg["destination"]
            r2, c2 = grid_size - scale(dest[1]), scale(dest[0])
            if grid[r2][c2] == ".":
                grid[r2][c2] = "*"

    for row in grid:
        print(" ".join(row))
    print("  W=Warehouse  A=Agent  *=Destination\n")


def export_top_performer_csv(report, source_file, output_path="top_performer.csv"):
    best = report.get("best_agent")
    if not best:
        print("No best agent to export.")
        return

    stats = report[best]
    file_exists = os.path.isfile(output_path)
    fieldnames = ["source_file", "agent", "packages_delivered", "total_distance", "efficiency"]

    with open(output_path, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow({
            "source_file": source_file,
            "agent": best,
            "packages_delivered": stats["packages_delivered"],
            "total_distance": stats["total_distance"],
            "efficiency": stats["efficiency"]
        })
    print(f"Top performer appended to '{output_path}'")


def main(input_file="data.json", reports_folder="reports"):
    print(f"\n=== FastBox Delivery Simulator ===")
    print(f"Input file: {input_file}\n")

    warehouses, agents, packages = load_data(input_file)
    print(f"Loaded {len(warehouses)} warehouses, {len(agents)} agents, {len(packages)} packages.")

    assignments = assign_packages(warehouses, agents, packages)
    print("\nPackage Assignments:")
    for aid, pkgs in assignments.items():
        pkg_ids = [p["id"] for p in pkgs]
        print(f"  {aid} → {pkg_ids if pkg_ids else '(no packages)'}")

    sim_results = simulate_delivery(warehouses, agents, assignments)
    report = generate_report(sim_results)

    print("\nDelivery Report:")
    for aid, stats in report.items():
        if aid == "best_agent":
            continue
        print(f"  {aid}: delivered={stats['packages_delivered']}, distance={stats['total_distance']}, efficiency={stats['efficiency']}")
    print(f"\n  🏆 Best Agent: {report['best_agent']}")

    base_name = os.path.splitext(os.path.basename(input_file))[0]
    report_path = os.path.join(reports_folder, f"report_{base_name}.json")
    save_report(report, output_path=report_path)

    visualise_routes(warehouses, agents, assignments)
    export_top_performer_csv(report, source_file=input_file)

    return report, base_name


def run_all_test_cases():
    REPORTS_FOLDER = "reports"
    os.makedirs(REPORTS_FOLDER, exist_ok=True)

    if os.path.isfile("top_performer.csv"):
        os.remove("top_performer.csv")
        print("Cleared old top_performer.csv — starting fresh.\n")
    if os.path.isfile("summary.json"):
        os.remove("summary.json")

    test_files = sorted(glob.glob("Python Assignment(Delivery System Test Cases)/test_case_*.json"))
    all_files = ["base_case.json"] + test_files

    print(f"Found {len(all_files)} input files to process.\n")
    print("=" * 50)

    summary = {}

    for f in all_files:
        if os.path.isfile(f):
            report, base_name = main(f, reports_folder=REPORTS_FOLDER)
            summary[base_name] = report
            print("=" * 50)
        else:
            print(f"  [SKIPPED] {f} not found.")

    overall_best_case = None
    overall_best_agent = None
    overall_best_eff = float("inf")

    for case_name, rep in summary.items():
        best = rep.get("best_agent")
        if best and rep[best]["efficiency"] < overall_best_eff:
            overall_best_eff = rep[best]["efficiency"]
            overall_best_agent = best
            overall_best_case = case_name

    summary_output = {
        "total_test_cases": len(summary),
        "overall_best_agent": {
            "agent": overall_best_agent,
            "test_case": overall_best_case,
            "efficiency": overall_best_eff
        },
        "results_by_test_case": summary
    }

    with open("summary.json", "w") as f:
        json.dump(summary_output, f, indent=4)

    print(f"\n✅ All done!")
    print(f"   • Individual reports → {REPORTS_FOLDER}/report_<name>.json")
    print(f"   • Top performers     → top_performer.csv")
    print(f"   • Full summary       → summary.json")
    print(f"\n🏆 Overall best: Agent {overall_best_agent} in {overall_best_case} (efficiency={overall_best_eff})")


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else "data.json"
    if arg == "all":
        run_all_test_cases()
    else:
        main(arg)