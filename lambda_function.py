import urllib.request
import json
import os
from dataclasses import dataclass
from typing import Optional

base_uri = "https://robertsspaceindustries.com"
graphql_uri = f"{base_uri}/graphql"
webhook_uri = os.environ.get('DISCORD_WEBHOOK_URL')
discord_message_mention = os.environ.get('DISCORD_MENTION_ROLE_ID')


@dataclass(frozen=True)
class ShipSaleNotificationDetails:
    # Fields used by _determine_title and _ship_type
    name: Optional[str]
    subtitle: Optional[str]
    is_warbond: Optional[bool]
    price_amount_cents: Optional[int]  # Raw integer price (in cents)
    shop_url_path: Optional[str]  # The relative path (e.g., /pledge/Standalone-Ships/Hull-E-10-Year)
    thumbnail_url_path: Optional[str]  # The relative path to the thumbnail


def execute(event):
    ships = get_lti_pledge_ships_page()
    dryrun = is_dryrun(event)
    send_discord_notification(ships, dryrun)


def is_dryrun(event) -> bool:
    if 'dryrun' not in event:
        return False

    dryRunFlag = event['dryrun']
    if isinstance(dryRunFlag, bool):
        return dryRunFlag

    if isinstance(dryRunFlag, str):
        return dryRunFlag.lower() in ['true', 'yes', 'y']

    # Catch-all, assume they wanted dry-run.
    return True


def data_to_bytes(obj):
    return str(json.dumps(obj)).encode("utf-8")


def get_lti_pledge_ships_page(page=1) -> [ShipSaleNotificationDetails]:
    print(f"Fetching page number {page}")
    limit = 10

    ship_payload = _create_ship_query_payload(page=page, limit=limit)
    response = urllib.request.urlopen(urllib.request.Request(
        method="POST",
        url=graphql_uri,
        headers={
            'accept': '*/*',
            'accept-language': 'en-US,en;q=0.9',
            'content-type': 'application/json'
        },
        data=data_to_bytes(ship_payload)
    ))

    lti_ships_slugs: [str] = []
    is_last = True
    for datum in json.loads(response.read()):
        if datum['data'] is not None:
            if datum['data']['store'] is not None:
                if datum['data']['store']['listing'] is not None:
                    listing = datum['data']['store']['listing']
                    if listing['resources'] is not None:
                        resources = listing['resources']
                        for ship in resources:
                            if ship is not None:
                                if ship['slug']:
                                    lti_ships_slugs.append(ship['slug'])
                    count = listing['count']
                    total = listing['totalCount']
                    count_so_far = limit * (page -1) + count
                    if count_so_far < total:
                        is_last = False

    lti_ships: [ShipSaleNotificationDetails] = []
    if len(lti_ships_slugs) > 0:
        ship_purchase_options_payload = _create_ship_buying_options_query_payload(lti_ships_slugs)

        response = urllib.request.urlopen(urllib.request.Request(
            method="POST",
            url=graphql_uri,
            headers={
                'accept': '*/*',
                'accept-language': 'en-US,en;q=0.9',
                'content-type': 'application/json'
            },
            data=data_to_bytes(ship_purchase_options_payload)
        ))

        for datum in json.loads(response.read()):
            if datum['data'] is not None:
                if datum['data']['store'] is not None:
                    if datum['data']['store']['search'] is not None:
                        search = datum['data']['store']['search']
                        count = search['count']
                        if count != len(lti_ships_slugs):
                            # todo: Alert of mismatch slug buying response
                            print("TODO ALERT")

                        if search['resources'] is not None:
                            resources = search['resources']
                            for resource in resources:
                                if resource is not None:
                                    if resource['gameItems'] is not None:
                                        game_items = resource['gameItems']
                                        for game_item in game_items:
                                            if game_item is not None:
                                                if game_item['name'] is not None:
                                                    if game_item['name'] == 'Lifetime Insurance':
                                                        price = None
                                                        price_object = resource['price']
                                                        if price_object is not None:
                                                            price = price_object['amount']

                                                        thumbnail = None
                                                        thumbnail_composer = resource['imageComposer']
                                                        if thumbnail_composer and len(thumbnail_composer) > 0:
                                                            thumbnail = thumbnail_composer[0]['url']
                                                        lti_ships.append(ShipSaleNotificationDetails(
                                                            name=resource['name'],
                                                            subtitle=resource['subtitle'],
                                                            is_warbond=resource['isWarbond'],
                                                            price_amount_cents=price,
                                                            shop_url_path=resource['url'],
                                                            thumbnail_url_path=thumbnail,
                                                        ))

    if is_last:
        if lti_ships is None or len(lti_ships) == 0:
            return []
        return lti_ships
    else:
        lti_ships.extend(get_lti_pledge_ships_page(page=page + 1))
        return lti_ships


def _create_ship_query_payload(limit=20, page=1):
    return [
        {
            "operationName": "GetBrowseSkusStandaloneShipByFilter",
            "variables": {
                "query": {
                    "page": page,
                    "limit": limit,
                    "skus": {
                        "filtersFromTags": {
                            "tagIdentifiers": [],
                            "facetIdentifiers": [
                                "extras-standalone-ships"
                            ]
                        },
                        "products": [
                            72
                        ]
                    },
                    "sort": {
                        "field": "weight",
                        "direction": "desc"
                    }
                }
            },
            "query": """
query GetBrowseSkusStandaloneShipByFilter($query: SearchQuery) {
  store(browse: true) {
    listing: search(query: $query) {
      resources {
        ...TyItemBrowseFragment
        __typename
      }
      count
      totalCount
      heapTagFiltersOptions {
        ...StoreListingHeapTagFiltersOptionsFragment
        __typename
      }
      standaloneShipFiltersOptions {
        ...StoreListingStandaloneShipFiltersOptions
        __typename
      }
      __typename
    }
    __typename
  }
}

fragment TyItemBrowseFragment on TyItem {
  id
  slug
  name
  title
  subtitle
  url
  body
  excerpt
  type
  media {
    thumbnail {
      slideshow
      storeSmall
      __typename
    }
    list {
      slideshow
      __typename
    }
    __typename
  }
  nativePrice {
    amount
    discounted
    discountDescription
    __typename
  }
  price {
    amount
    discounted
    taxDescription
    discountDescription
    __typename
  }
  stock {
    ...TyStockFragment
    __typename
  }
  tags {
    ...TyHeapTagFragment
    __typename
  }
  ... on TySku {
    imageComposer {
      ...ImageComposerFragment
      __typename
    }
    ...TySkuBrowseFragment
    __typename
  }
  ... on TyProduct {
    imageComposer {
      ...ImageComposerFragment
      __typename
    }
    ...TyProductBrowseFragment
    __typename
  }
  __typename
}

fragment TySkuBrowseFragment on TySku {
  label
  customizable
  isWarbond
  isPackage
  isVip
  isDirectCheckout
  __typename
}

fragment TyProductBrowseFragment on TyProduct {
  skus {
    id
    title
    isDirectCheckout
    __typename
  }
  isVip
  __typename
}

fragment TyStockFragment on TyStock {
  unlimited
  show
  available
  backOrder
  qty
  backOrderQty
  level
  __typename
}

fragment TyHeapTagFragment on HeapTag {
  name
  __typename
}

fragment ImageComposerFragment on ImageComposer {
  name
  slot
  url
  __typename
}

fragment StoreListingHeapTagFiltersOptionsFragment on HeapTagGroup {
  groupIdentifier
  facets {
    facet
    tagIdentifiers {
      identifier
      name
      __typename
    }
    __typename
  }
  __typename
}

fragment StoreListingStandaloneShipFiltersOptions on StandaloneShipFilters {
  warbond {
    label
    value
    __typename
  }
  price {
    from
    to
    __typename
  }
  __typename
}
"""
        }
    ]


def _create_ship_buying_options_query_payload(slugs: [str]):
    """
    :return:
    """
    if not slugs:
        return None

    return [
        {
            "operationName": "GetSkus",
            "variables": {
                "query": {
                    "skus": {
                        "slugs": slugs,
                        "imageComposer": [
                            # {
                            # "name": "1024",
                            # "size": "SIZE_900",
                            # "ratio": "RATIO_16_9",
                            # "extension": "WEBP"
                            # },
                            # {
                            # "name": "1440",
                            # "size": "SIZE_1000",
                            # "ratio": "RATIO_16_9",
                            # "extension": "WEBP"
                            # },
                            # {
                            # "name": "2048",
                            # "size": "SIZE_1100",
                            # "ratio": "RATIO_16_9",
                            # "extension": "WEBP"
                            # }
                        ],
                        "unslottedMedia": False,
                        "items": {
                            "imageComposer": [
                                # {
                                # "name": "1024",
                                # "size": "SIZE_900",
                                # "ratio": "RATIO_16_9",
                                # "extension": "WEBP"
                                # },
                                # {
                                # "name": "1440",
                                # "size": "SIZE_1000",
                                # "ratio": "RATIO_16_9",
                                # "extension": "WEBP"
                                # },
                                # {
                                # "name": "2048",
                                # "size": "SIZE_1100",
                                # "ratio": "RATIO_16_9",
                                # "extension": "WEBP"
                                # }
                            ]
                        }
                    }
                }
            },
            "query": """
query GetSkus($query: SearchQuery!) {
  store(name: \"pledge\", browse: true) {
    search(query: $query) {
      count
      resources {
        id
        title
        name
        ...TySkuWithoutParentProductFragment
        __typename
      }
      __typename
    }
    __typename
  }
  }

fragment TySkuWithoutParentProductFragment on TySku {
  id
  slug
  productId
  title
  subtitle
  label
  body
  excerpt
  url
  type
  isDirectCheckout
  isVip
  isWarbond
  isPackage
  hasShips
  customizable
  ships {
    ...RSIShipBaseWithMediasFragment
    __typename
  }
  gameItems {
    name
    kind
    code
    description
    hasGamePurchase
    isApplicableOnMoreThanOneShip
    imageComposer {
      slot
      name
      url
      __typename
    }
    media {
      thumbnail {
        storeSmall
        __typename
      }
      __typename
    }
    __typename
  }
  stock {
    ...TyStockFragment
    __typename
  }
  nativePrice {
    ...TyBrowsePriceFragment
    __typename
  }
  price {
    ...TyBrowseTaxedPriceFragment
    __typename
  }
  imageComposer {
    ...ImageComposerFragment
    __typename
  }
  __typename
  }

fragment TyStockFragment on TyStock {
  unlimited
  show
  available
  backOrder
  qty
  backOrderQty
  level
  __typename
  }

fragment ImageComposerFragment on ImageComposer {
  name
  slot
  url
  __typename
  }

fragment TyBrowsePriceFragment on TyBrowsePrice {
  amount
  discounted
  discountDescription
  __typename
  }

fragment TyBrowseTaxedPriceFragment on TyBrowseTaxedPrice {
  amount
  discounted
  discountDescription
  taxDescription
  __typename
  }

fragment RSIShipBaseWithMediasFragment on RSIShip {
  ...RSIShipBaseFragment
  manufacturer {
    name
    __typename
  }
  imageComposer {
    ...ImageComposerFragment
    __typename
  }
  __typename
  }

fragment RSIShipBaseFragment on RSIShip {
  id
  title
  name
  url
  slug
  type
  focus
  msrp
  purchasable
  productionStatus
  lastUpdate
  publishStart
  __typename
  }
"""
        }
    ]


def send_discord_notification(ships: [ShipSaleNotificationDetails], dryrun: bool):
    payload = _create_webhook_payload(ships)

    if dryrun:
        print(json.dumps(payload))
    else:
        urllib.request.urlopen(urllib.request.Request(
            method="POST",
            url=webhook_uri,
            headers={
                'content-type': 'application/json',
                'User-Agent': 'Mozilla/5.0 (X11; U; Linux i686) Gecko/20071127 Firefox/2.0.0.11'
            },
            data=data_to_bytes(payload)
        ))

def _create_webhook_payload(ships):
    if not ships:
        return {
            "content": "There are not currently any ships on sale with LTI.",
            "embeds": [],
            "attachments": []
        }

    embeds = []
    for ship in ships:
        embeds.append({
            "title": _determine_title(ship),
            "url": _determine_shop_url(ship),
            "color": 5814783,
            "fields": [
                {
                    "name": "Price",
                    "value": _determine_price(ship),
                    "inline": True
                },
                {
                    "name": "Type",
                    "value": _ship_type(ship),
                    "inline": True
                }
            ],
            "image": {
                "url": _determine_thumbnail_url(ship)
            }
        })
    return {
        "content": _determine_content(),
        "embeds": embeds,
        "attachments": []
    }


def _determine_content():
    message = "The below ships are on sale with Life Time Insurance (LTI).\n_ _"
    if discord_message_mention is not None:
        return f"<@&{discord_message_mention}> {message}"
    return message


def _determine_title(ship: ShipSaleNotificationDetails):
    if ship is not None and ship.name is not None:
        if ship.is_warbond:
            return f"Warbond {ship.name}"
        else:
            return ship.name
    return "Unknown"


def _ship_type(ship: ShipSaleNotificationDetails):
    if ship is not None and ship.subtitle:
        subtitle = ship.subtitle
        if 'Standalone Ships' == subtitle:
            return 'Ship'
        elif 'Package' == subtitle:
            return 'Game Package'
    return 'Unknown'


def _determine_price(ship: ShipSaleNotificationDetails):
    if ship is not None and ship.price_amount_cents is not None:
        return f"${(ship.price_amount_cents / 100):,.2f}"
    return "Unknown"


def _media_url(url):
    if "https://" in url:
        return url
    else:
        # these urls are used for rel links, so if it doesn't include the base we need to assume its from RSI.
        return f"{base_uri}{url}"


def _determine_thumbnail_url(ship: ShipSaleNotificationDetails):
    if ship is not None and ship.thumbnail_url_path is not None:
        url = ship.thumbnail_url_path
        return _media_url(url=url)
    else:
        return "https://www.google.com/images/errors/robot.png"


def _determine_shop_url(ship: ShipSaleNotificationDetails):
    if ship is not None and ship.shop_url_path is not None:
        return _media_url(url=ship.shop_url_path)
    else:
        return "https://www.google.com/images/errors/robot.png"


def lambda_handler(event, context):
    execute(event)


if __name__ == "__main__":
    execute({
        "dryrun": True
    })
